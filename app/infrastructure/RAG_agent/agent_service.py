import os
import json
from uuid import UUID

from dotenv import load_dotenv
from fastapi import HTTPException
from langchain.agents import AgentExecutor
from langchain.agents.format_scratchpad import format_log_to_messages
from langchain.agents.json_chat.prompt import TEMPLATE_TOOL_RESPONSE
from langchain.memory import ConversationTokenBufferMemory
from langchain.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
    PromptTemplate,
    SystemMessagePromptTemplate,
)
from langchain.tools.render import render_text_description
from langchain.tools.retriever import create_retriever_tool
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableParallel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

# from langchain.retrievers import AzureCognitiveSearchRetriever
from langchain_community.retrievers.azure_cognitive_search import AzureCognitiveSearchRetriever
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import AzureChatOpenAI
from sqlalchemy.orm import Session

from app.infrastructure.analytics_agent.agent_memory import AnalyticsAgentChatMessageHistory
from app.infrastructure.RAG_agent.output_parser import CustomJSONAgentOutputParser
from app.infrastructure.RAG_agent.prompts.system_prompt import (
    SYSTEM_MESSAGE_TEMPLATE,
)

load_dotenv()

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder


class RAGAgent:
    def __init__(self, chat_id: UUID, db_session: Session):
        # setting up retriever
        self.retriever = AzureCognitiveSearchRetriever(
            service_name=os.getenv("AZURE_COGNITIVE_SEARCH_SERVICE_NAME"),
            index_name=os.getenv("AZURE_COGNITIVE_SEARCH_INDEX_NAME"),
            api_key=os.getenv("AZURE_COGNITIVE_SEARCH_API_KEY"),
            content_key="content",
            top_k=4,
        )

        self.llm = AzureChatOpenAI(
            deployment_name=os.getenv("GPT4_TURBO_DEPLOYMENT_NAME"),
            azure_endpoint=os.getenv("GPT4_TURBO_AZURE_OPENAI_ENDPOINT"),
            openai_api_version=os.getenv("GPT4_TURBO_OPENAI_API_VERSION"),
            openai_api_key=os.getenv("GPT4_TURBO_AZURE_OPENAI_API_KEY"),
            temperature=0,
        )

    def test_azure_ai_logic(self, prompt: str, chat_history):
        contextualize_q_system_prompt = """Given a chat history and the latest user question \
        which might reference context in the chat history, formulate a standalone question \
        which can be understood without the chat history. Do NOT answer the question, \
        just reformulate it if needed and otherwise return it as is."""
        contextualize_q_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", contextualize_q_system_prompt),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{question}"),
            ]
        )
        contextualize_q_chain = contextualize_q_prompt | self.llm | StrOutputParser()

        def format_docs(docs):
            data = "\n\n".join(doc.page_content for doc in docs)
            return data

        custom_rag_prompt = PromptTemplate.from_template(SYSTEM_MESSAGE_TEMPLATE)

        qa_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", custom_rag_prompt),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{question}"),
            ]
        )

        def contextualized_question(input: dict):
            if input.get("chat_history"):
                return contextualize_q_chain
            else:
                return input["question"]

        rag_chain = (
            # RunnablePassthrough.assign(context=(lambda x: format_docs(x["context"])))
            RunnablePassthrough.assign(context=contextualized_question | self.retriever | format_docs)
            | qa_prompt
            | self.llm
            | StrOutputParser()
        )

        rag_chain_with_source = RunnableParallel(
            {"context": self.retriever, "question": RunnablePassthrough()}
        ).assign(answer=rag_chain)

        for event in rag_chain_with_source.stream({"question": prompt, "chat_history": chat_history}):
            if event and event.get("answer", None):
                yield event, "answer"
            elif event and event.get("context", None):
                yield event, "documents"
            else:
                continue

    def invoke(self, user_query: str, chat_history):
        message_history = []

        for message_obj in chat_history:
            if message_obj.role.value == "Assistant":
                message_history.append(AIMessage(content=message_obj.text))
            elif message_obj.role.value == "User":
                message_history.append(HumanMessage(content=message_obj.text))
            else:
                print(message_obj.__dict__)
        print(message_history)
        # try:
        for response_text, response_type in self.test_azure_ai_logic(user_query, message_history):
            if response_text and response_type == "answer":
                yield response_text["answer"], response_type
            if response_text and response_type == "documents":
                yield response_text["context"], response_type
        # except Exception as e:
        #     raise HTTPException(status_code=500, detail=f"RAG Agent failed: {e}")
