from typing import List
from uuid import UUID

from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage
from langchain_core.messages.ai import AIMessage
from langchain_core.messages.human import HumanMessage
from sqlalchemy.orm import Session

from app.enums.message_enums import MessageRole
from app.models.maindb.message import Message


class AnalyticsAgentChatMessageHistory(BaseChatMessageHistory):
    def __init__(self, chat_id: UUID, db_session: Session):
        self.chat_id = chat_id
        self.db_session = db_session
        self._messages = self._get_messages_from_db()

    def _get_messages_from_db(self):
        old_messages = []
        query = (
            self.db_session.query(Message.text, Message.role, Message.sql_query)
            .filter(Message.chat_id == self.chat_id)
            .order_by(Message.created_at)
        )

        # Execute the query and fetch the results
        result_rows = query.all()
        for row in result_rows:
            if row.role == MessageRole.User:
                old_messages.append(HumanMessage(content=row.text))
            elif row.role == MessageRole.Assistant:
                agent_message = row.text
                if row.sql_query:
                    agent_message = f"{agent_message}\n\nSQL query I created: {row.sql_query}"

                old_messages.append(AIMessage(content=agent_message))

        return old_messages
    
    @property
    def messages(self):
        return self._messages

    def add_message(self, message: BaseMessage) -> None:
        """Add a message to the session memory"""
        self._messages.append(message)

    def clear(self) -> None:
        """Clear session memory"""
        self._messages.clear()
