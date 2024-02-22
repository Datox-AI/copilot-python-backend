import json
import uuid
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.backend.session import create_maindb_session
from app.enums.chat_enums import ChatType
from app.enums.message_enums import MessageRole, MessageStatus
from app.models.maindb import Chat, Message
from app.schemas.identity.current_user import CurrentUser
from app.schemas.message import MessageMapper
from app.schemas.message.message_request import CreateMessageRequest, UpdateMessageRequest
from app.shared.auth.azure_scheme import current_user
from app.services.files.user_files_services import UserFileService
from app.services.files.lang_chain_file_service import LangChainService

from .message_create_stream import OpenAIChatStream


class UserMessageService:
    def __init__(
        self,
        user: Annotated[CurrentUser, Depends(current_user)],
        chat_id: UUID,
        session: Annotated[Session, Depends(create_maindb_session)],
    ) -> None:
        self.session = session
        self.user = user
        self.chat_id = chat_id
        self.streamer = OpenAIChatStream()
        self.file_service = UserFileService(user, session)
        self.langchain_service = LangChainService()

    def create_message(self, request: CreateMessageRequest):
        self._check_chat_exists(chat_id=self.chat_id)
        reply_message = None
        if request.replyTo:
            reply_message = self.session.query(Message).filter(Message.id == request.replyTo).first()
            if not reply_message:
                raise HTTPException(
                    status_code=404, detail=f"Message object under {request.replyTo} id does not exist"
                )
        file_exist = None
        file_contents = []
        if request.files:
            for file_id in request.files:
                file_content = self.file_service.download_file(file_id)
                if file_content:
                    file_exist = True
                    file_contents.append(file_content)
        # Сохранение нового пользовательского сообщения
        new_user_message = Message(
            id=uuid.uuid4(),
            chat_id=self.chat_id,
            text=request.prompt,
            status=MessageStatus.Success,
            role=MessageRole.User,
            reply_to_id=request.replyTo if request.replyTo else None,
        )
        self.session.add(new_user_message)
        self.session.commit()

        # Генерация ответа и follow-up вопросов
        def response_generator():
            message_objs = self.session.query(Message).filter(Message.chat_id == self.chat_id).all()
            if not file_exist:
                full_response = ""
                for response_text, is_question, follow_up_questions, error_message in self.streamer.stream_responses(
                    message_objs, request.prompt, reply_message
                ):
                    if error_message:
                        yield f"data: {json.dumps({'Error': error_message, 'Type': 'Error'})}\n\n"
                        continue  # Пропускаем оставшуюся часть цикла в случае ошибки

                    if response_text and not is_question:
                        full_response += response_text
                        yield f"data: {json.dumps({'Type': 'Text', 'Text': response_text})}\n\n"

                    if is_question:
                        yield f"data: {json.dumps({'Questions': follow_up_questions, 'Type': 'Questions'})}\n\n"
                    # Создание и сохранение нового сообщения от ассистента с follow-up вопросами

                new_assistant_message = Message(
                    id=uuid.uuid4(),
                    chat_id=self.chat_id,
                    text=full_response,
                    follow_up_questions=follow_up_questions,
                    status=MessageStatus.Success,
                    role=MessageRole.Assistant,
                    prompt_id=new_user_message.id,
                )
                self.session.add(new_assistant_message)
                self.session.commit()
            response = self.lang_chain_service.process_document_and_generate_response(
                file_content_bytes=file_contents, prompt=request.prompt
            )
            yield f"data: {json.dumps({'Type': 'Text', 'Text': response})}\n\n"

        return response_generator()

    def get_messages(self, chat_id: UUID):
        self._check_chat_exists(chat_id=self.chat_id)
        message_objs = (
            self.session.query(Message).filter(Message.chat_id == chat_id).order_by(Message.created_at.asc())
        )

        return [MessageMapper.map_to_user_message_response(message_obj) for message_obj in message_objs]

    def delete_message(self, chat_id: UUID, message_id: UUID):
        message = self.session.query(Message).filter(Message.id == message_id, Message.chat_id == chat_id).first()
        if message:
            self.session.delete(message)
            self.session.commit()
            return True
        return False

    def update_message(self, chat_id: UUID, message_id: UUID, updated_data: UpdateMessageRequest):
        self._check_chat_exists(chat_id=self.chat_id)
        message_obj = self.session.query(Message).filter(Message.id == message_id, Message.chat_id == chat_id).first()
        if message_obj:
            if message_obj.id != updated_data.id:
                raise HTTPException(status_code=400, detail=f"Message id you provided ({message_id}) is wrong")
            message_obj.pinned = updated_data.pinned
            if message_obj.pinned:
                message_obj.pinned_date = datetime.now()
            self.session.commit()

            return message_obj
        else:
            raise HTTPException(status_code=404, detail="Message not found")

    def delete_messages_batch(self, chat_id: UUID, message_ids: list):
        self.session.query(Message).filter(Message.id.in_(message_ids), Message.chat_id == chat_id).delete(
            synchronize_session=False
        )
        self.session.commit()

    def _check_chat_exists(self, chat_id: UUID) -> bool:
        self.chat_obj = self.session.query(Chat).filter(Chat.id == chat_id).first()
        if not self.chat_obj:
            raise HTTPException(status_code=404, detail=f"Chat object under {chat_id} id does not exist")
        if self.chat_obj.type != ChatType.Analytics:
            raise HTTPException(
                status_code=400, detail=f"Chat object under {chat_id} id does not have Analytics as its chat type"
            )
