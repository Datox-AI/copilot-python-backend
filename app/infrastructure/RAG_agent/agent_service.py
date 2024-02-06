import os
from fastapi import HTTPException
from uuid import UUID
from dotenv import load_dotenv
from sqlalchemy.orm import Session

from langchain_core.prompts import PromptTemplate
from langchain.tools.retriever import create_retriever_tool
from langchain.agents import AgentExecutor
from langchain.prompts import PromptTemplate, ChatPromptTemplate
from langchain_openai import AzureChatOpenAI
from langchain.memory import ConversationTokenBufferMemory
from langchain_core.prompts import ChatPromptTemplate

# from langchain.retrievers import AzurzeCognitiveSearchRetriever
from langchain_community.retrievers.azure_cognitive_search import AzureCognitiveSearchRetriever
from langchain.prompts import HumanMessagePromptTemplate, MessagesPlaceholder, SystemMessagePromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain.tools.render import render_text_description
from langchain.agents.format_scratchpad import format_log_to_messages
from langchain.agents.json_chat.prompt import TEMPLATE_TOOL_RESPONSE


from app.infrastructure.rag_agent.prompts.system_prompt import (
    SYSTEM_MESSAGE_TEMPLATE,
    TOOLS_TEMPLATE,
    RETRIEVER_PROMPT,
)
from app.infrastructure.rag_agent.output_parser import CustomJSONAgentOutputParser
from app.infrastructure.analytics_agent.agent_memory import AnalyticsAgentChatMessageHistory

load_dotenv()


class RAGAgent:
    def __init__(self, chat_id: UUID, db_session: Session):
        # setting up retriever
        print(os.getenv("AZURE_COGNITIVE_SEARCH_SERVICE_NAME"), "service name")
        self.retriever = AzureCognitiveSearchRetriever(
            service_name=os.getenv("AZURE_COGNITIVE_SEARCH_SERVICE_NAME"),
            index_name=os.getenv("AZURE_COGNITIVE_SEARCH_INDEX_NAME"),
            api_key=os.getenv("AZURE_COGNITIVE_SEARCH_API_KEY"),
            content_key="content",
            top_k=1,
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

    def invoke(self, user_query: str):
        try:
            agent_response = self.agent_executor.invoke({"input": user_query})
            searched_documents = []
            print(agent_response, " reponse ")

            if agent_response["document_searched_query"] != "":
                document_searched_query = agent_response["document_searched_query"]
                self.retriever.top_k = 5
                searched_documents = self.retriever.invoke(input=document_searched_query)

            return agent_response, searched_documents

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"RAG Agent failed: {e}")
