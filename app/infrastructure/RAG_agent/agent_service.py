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

# from langchain.retrievers import AzureCognitiveSearchRetriever
from langchain_community.retrievers.azure_cognitive_search import AzureCognitiveSearchRetriever
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import AzureChatOpenAI
from sqlalchemy.orm import Session

from app.infrastructure.analytics_agent.agent_memory import AnalyticsAgentChatMessageHistory
from app.infrastructure.RAG_agent.output_parser import CustomJSONAgentOutputParser
from app.infrastructure.RAG_agent.prompts.system_prompt import (
    RETRIEVER_PROMPT,
    SYSTEM_MESSAGE_TEMPLATE,
    TOOLS_TEMPLATE,
)

load_dotenv()


class RAGAgent:
    def __init__(self, chat_id: UUID, db_session: Session):
        # setting up retriever
        self.retriever = AzureCognitiveSearchRetriever(
            service_name=os.getenv("AZURE_COGNITIVE_SEARCH_SERVICE_NAME"),
            index_name=os.getenv("AZURE_COGNITIVE_SEARCH_INDEX_NAME"),
            api_key=os.getenv("AZURE_COGNITIVE_SEARCH_API_KEY"),
            content_key="content",
            top_k=2,
        )

        retriever_prompt = PromptTemplate.from_template(RETRIEVER_PROMPT)
        tool = create_retriever_tool(
            self.retriever,
            "search_from_share_point",
            "Searches and returns documents from sharepoint",
            document_prompt=retriever_prompt,
        )
        self.tools = [tool]
        # creating an agent and agent executor
        self.agent_prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessagePromptTemplate.from_template(template=SYSTEM_MESSAGE_TEMPLATE),
                MessagesPlaceholder(variable_name="chat_history", optional=True),
                HumanMessagePromptTemplate.from_template(TOOLS_TEMPLATE),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )
        self.output_parser = CustomJSONAgentOutputParser()
        self.llm = AzureChatOpenAI(
            deployment_name=os.getenv("GPT4_TURBO_DEPLOYMENT_NAME"),
            azure_endpoint=os.getenv("GPT4_TURBO_AZURE_OPENAI_ENDPOINT"),
            openai_api_version=os.getenv("GPT4_TURBO_OPENAI_API_VERSION"),
            openai_api_key=os.getenv("GPT4_TURBO_AZURE_OPENAI_API_KEY"),
            temperature=0,
        )
        json_agent = self._create_custom_json_chat_agent()
        # here I am using Analytics Agent's custom history class because it is also applicable to this agent
        message_history = AnalyticsAgentChatMessageHistory(chat_id=chat_id, db_session=db_session)
        memory = ConversationTokenBufferMemory(
            memory_key="history",
            chat_memory=message_history,
            llm=self.llm,
            max_token=5000,
            output_key="output",
            input_key="input",
            return_messages=True,
        )
        self.agent_executor = AgentExecutor.from_agent_and_tools(
            agent=json_agent,
            tools=self.tools,
            verbose=True,
            memory=memory,
        )

    def _create_custom_json_chat_agent(self):
        missing_vars = {"tools", "tool_names", "agent_scratchpad"}.difference(self.agent_prompt.input_variables)
        if missing_vars:
            raise ValueError(f"Prompt missing required variables: {missing_vars}")

        self.agent_prompt = self.agent_prompt.partial(
            tools=render_text_description(list(self.tools)),
            tool_names=", ".join([t.name for t in self.tools]),
        )
        llm_with_stop = self.llm.bind(stop=["\nObservation"])

        agent = (
            RunnablePassthrough.assign(
                agent_scratchpad=lambda x: format_log_to_messages(
                    x["intermediate_steps"], template_tool_response=TEMPLATE_TOOL_RESPONSE
                )
            )
            | self.agent_prompt
            | llm_with_stop
            | self.output_parser
        )
        return agent

    def test_azure_ai_logic(self, prompt: str):
        def format_docs(docs):
            data = "\n\n".join(doc.page_content for doc in docs)
            return data

        template = """You're an AI assistant analyzing a document. 
        This could be an invoice, a report, or any other type of documentation. 
        If it's an invoice, consider that the data might be used for various reports: monthly, quarterly, by client, by product or service, etc. 
        Capture every crucial detail: names, figures, numbers, dates, events, and other significant points. 
        The summary should be comprehensive, detailing the core content without adding any extraneous remarks

        {context}

        Question: {question}

        Detail Answer:"""
        custom_rag_prompt = PromptTemplate.from_template(template)

        rag_chain = (
            RunnablePassthrough.assign(context=(lambda x: format_docs(x["context"])))
            | custom_rag_prompt
            | self.llm
            | StrOutputParser()
        )

        rag_chain_with_source = RunnableParallel(
            {"context": self.retriever, "question": RunnablePassthrough()}
        ).assign(answer=rag_chain)
        for event in rag_chain_with_source.stream(prompt):
            if event and event.get("answer", None):
                yield event, "answer"
            elif event and event.get("context", None):
                yield event, "documents"
            else:
                continue

    def invoke(self, user_query: str):
        try:
            for response_text, response_type in self.test_azure_ai_logic(user_query):
                if response_text and response_type == "answer":
                    yield response_text["answer"], response_type
                if response_text and response_type == "documents":
                    yield response_text["context"], response_type
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"RAG Agent failed: {e}")
