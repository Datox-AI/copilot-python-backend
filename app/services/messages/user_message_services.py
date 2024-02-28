import json
import uuid
import asyncio
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException
from fastapi.responses import StreamingResponse, PlainTextResponse
from sqlalchemy.orm import Session
from sqlalchemy.future import select

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


    # async def create_message(self, request: CreateMessageRequest):
    #     self._check_chat_exists(chat_id=self.chat_id)
    #     reply_message = None
    #     if request.replyTo:
    #         reply_message = self.session.query(Message).filter(Message.id == request.replyTo).first()
    #         if not reply_message:
    #             raise HTTPException(
    #                 status_code=404, detail=f"Message object under {request.replyTo} id does not exist"
    #             )
    #     file_exist = None
    #     file_contents = []
    #     if request.files:
    #         for file_id in request.files:
    #             file_content = self.file_service.download_file(file_id)
    #             if file_content:
    #                 file_exist = True
    #                 file_contents.append(file_content)
    #     # Сохранение нового пользовательского сообщения
    #     new_user_message = Message(
    #         id=uuid.uuid4(),
    #         chat_id=self.chat_id,
    #         text=request.prompt,
    #         status=MessageStatus.Success,
    #         role=MessageRole.User,
    #         reply_to_id=request.replyTo if request.replyTo else None,
    #     )
    #     self.session.add(new_user_message)
    #     self.session.commit()

    #     # Генерация ответа и follow-up вопросов
    #     def response_generator():
    #         message_objs = self.session.query(Message).filter(Message.chat_id == self.chat_id).all()
    #         full_response = ""
    #         for response_text, is_question, follow_up_questions, error_message in self.streamer.stream_responses(
    #             message_objs, request.prompt, reply_message
    #         ):
    #             if error_message:
    #                 yield f"data: {json.dumps({'Error': error_message, 'Type': 'Error'})}\n\n"
    #                 continue  # Пропускаем оставшуюся часть цикла в случае ошибки

    #             if response_text and not is_question:
    #                 full_response += response_text
    #                 yield f"data: {json.dumps({'Type': 'Text', 'Text': response_text})}\n\n"

    #             if is_question:
    #                 yield f"data: {json.dumps({'Questions': follow_up_questions, 'Type': 'Questions'})}\n\n"
    #             # Создание и сохранение нового сообщения от ассистента с follow-up вопросами

    #         new_assistant_message = Message(
    #             id=uuid.uuid4(),
    #             chat_id=self.chat_id,
    #             text=full_response,
    #             follow_up_questions=follow_up_questions,
    #             status=MessageStatus.Success,
    #             role=MessageRole.Assistant,
    #             prompt_id=new_user_message.id,
    #         )
    #         self.session.add(new_assistant_message)
    #         self.session.commit()

    #     return response_generator()

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
        file_contents = []
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
        
        if request.files:
            file_contents = [
                self.file_service.download_file(file_id) for file_id in request.files
            ]
            print(file_contents)
            responses = [
                self.langchain_service.process_document_and_generate_response(content, request.prompt)
                for content, media_type in file_contents
            ]
            # full_response = " ".join(responses)
            print(responses)
            # return PlainTextResponse(content=responses, status_code=200)
        else:
            return StreamingResponse(self._process_text_query_and_respond(request, new_user_message, reply_message), media_type="text/event-stream")

    def _process_text_query_and_respond(self, request, new_user_message, reply_message):
        def response_generator():
            message_objs = self.session.query(Message).filter(Message.chat_id == self.chat_id).all()
            full_response = ""
            for response_text, is_question, follow_up_questions, error_message in self.streamer.stream_responses(
                message_objs, request.prompt, reply_message
            ):
                if error_message:
                    yield f"data: {json.dumps({'Error': error_message, 'Type': 'Error'})}\n\n"
                    continue

                if response_text and not is_question:
                    full_response += response_text
                    yield f"data: {json.dumps({'Type': 'Text', 'Text': response_text})}\n\n"

                if is_question:
                    yield f"data: {json.dumps({'Questions': follow_up_questions, 'Type': 'Questions'})}\n\n"

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

        return response_generator()
        
        
    # async def create_message(self, request: CreateMessageRequest):
    #     # Проверка существования чата
    #     self._check_chat_exists(chat_id=self.chat_id)

    #     # Определение reply_message, если есть
    #     reply_message = None
    #     if request.replyTo:
    #         reply_message = await self.session.query(Message).filter(Message.id == request.replyTo).first()
    #         if not reply_message:
    #             raise HTTPException(
    #                 status_code=404, detail=f"Message object under {request.replyTo} id does not exist"
    #             )

    #     # Создание и сохранение нового пользовательского сообщения в базе данных
    #     new_user_message = Message(
    #         id=uuid.uuid4(),
    #         chat_id=self.chat_id,
    #         text=request.prompt,
    #         status=MessageStatus.Success,
    #         role=MessageRole.User,
    #         reply_to_id=request.replyTo if request.replyTo else None,
    #     )
    #     self.session.add(new_user_message)
    #     self.session.commit()
        
    #     if request.files:
    #         file_contents = await asyncio.gather(*[
    #             self.file_service.download_file(file_id) for file_id in request.files
    #         ])
    #         responses = await asyncio.gather(*[
    #             self.langchain_service.process_document_and_generate_response(content, request.prompt)
    #             for content in file_contents
    #         ])
    #         full_response = " ".join(responses)
    #         await self._save_and_send_response(new_user_message, full_response)
    #     else:
    #         print("fffffff")
    #         await self._process_text_query_and_respond(request, new_user_message, reply_message)

    # async def _process_text_query_and_respond(self, request, new_user_message, reply_message):
    #     print("aaaaaaa")

    #     def response_generator():
    #         print("bbbbbbb")
    #         full_response = ""
    #         follow_up_questions = None
    #         print(request.prompt, new_user_message, reply_message)

    #         try:
    #             for response_text, is_question, questions, error_message in self.streamer.stream_responses(
    #                 [new_user_message], request.prompt, reply_message
    #             ):
    #                 if error_message:
    #                     yield f"data: {json.dumps({'Error': error_message, 'Type': 'Error'})}\n\n"
    #                 else:
    #                     if response_text:
    #                         full_response += response_text
    #                         yield f"data: {json.dumps({'Type': 'Text', 'Text': response_text})}\n\n"
    #                     if is_question:
    #                         follow_up_questions = questions
    #                         yield f"data: {json.dumps({'Questions': follow_up_questions, 'Type': 'Questions'})}\n\n"
    #         except Exception as e:
    #             yield f"data: {json.dumps({'Error': str(e), 'Type': 'Error'})}\n\n"

    #         if full_response:
    #             new_assistant_message = Message(
    #                 id=uuid.uuid4(),
    #                 chat_id=self.chat_id,
    #                 text=full_response,
    #                 follow_up_questions=follow_up_questions,
    #                 status=MessageStatus.Success,
    #                 role=MessageRole.Assistant,
    #                 prompt_id=new_user_message.id,
    #             )
    #             self.session.add(new_assistant_message)
    #             self.session.commit()

    #     return StreamingResponse(response_generator(), media_type="text/event-stream")

    # async def _process_file_and_respond(self, request, new_user_message, combined_file_content):
    #     try:
    #         response_text = await self.langchain_service.process_document_and_generate_response(
    #             combined_file_content, request.prompt
    #         )
    #         await self._save_and_send_response(new_user_message, response_text)
    #     except Exception as e:
    #         print(f"Ошибка обработки файла: {e}")

    # async def _save_and_send_response(self, new_user_message, response_text):
    #     new_assistant_message = Message(
    #         id=uuid.uuid4(),
    #         chat_id=self.chat_id,
    #         text=response_text,
    #         status=MessageStatus.Success,
    #         role=MessageRole.Assistant,
    #         prompt_id=new_user_message.id,  # Предполагается, что у объекта запроса есть атрибут id
    #     )
    #     await self.session.add(new_assistant_message)
    #     await self.session.commit()

    #     async def sse_generator():
    #         try:
    #             sse_data = json.dumps({'Type': 'Text', 'Text': response_text})
    #             yield f"data: {sse_data}\n\n"
    #         except Exception as e:
    #             error_data = json.dumps({'Type': 'Error', 'Error': str(e)})
    #             yield f"data: {error_data}\n\n"
    #     return StreamingResponse(sse_generator(), media_type="text/event-stream")

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
