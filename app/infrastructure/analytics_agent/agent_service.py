import os
import urllib
from typing import Dict
from uuid import UUID

from dotenv import load_dotenv
from langchain.agents import AgentExecutor, LLMSingleActionAgent
from langchain.agents.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain.chains.llm import LLMChain
from langchain.memory import ConversationTokenBufferMemory
from langchain_openai import AzureChatOpenAI
from sqlalchemy.engine import create_engine
from sqlalchemy.engine.base import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from snowflake.sqlalchemy import URL


from app.infrastructure.analytics_agent.agent_memory import AnalyticsAgentChatMessageHistory
from app.infrastructure.analytics_agent.azure_storage_manager import AzureBlobStorageManager
from app.infrastructure.analytics_agent.database_tools import CustomSQLDatabase, QuerySaveSQLDataBaseTool
from app.infrastructure.analytics_agent.output_parser import CustomOutputParser
from app.infrastructure.analytics_agent.prompt_template import CustomPromptTemplate
from app.infrastructure.analytics_agent.prompts.system_prompt import sql_helper_prompt_template
from app.infrastructure.analytics_agent.prompts.tool_prompts import sql_db_query_description, sql_db_schema_description
from app.infrastructure.analytics_agent.token_counter import TokenCounter
from app.models.maindb import Chat

load_dotenv()


class DataAnalyticAgent:
    def __init__(self, snowflake_engine: Engine, chat_id: UUID, db_session: Session):
        self.llm_chat_model = AzureChatOpenAI(
            deployment_name=os.getenv("GPT4_TURBO_DEPLOYMENT_NAME"),
            azure_endpoint=os.getenv("GPT4_TURBO_AZURE_OPENAI_ENDPOINT"),
            openai_api_version=os.getenv("GPT4_TURBO_OPENAI_API_VERSION"),
            openai_api_key=os.getenv("GPT4_TURBO_AZURE_OPENAI_API_KEY"),
            temperature=0,
            streaming=True,
        )
        # initiating our db manager and assigning blob manager to our db
        self.db = CustomSQLDatabase(snowflake_engine, view_support=True)
        self.azure_blob_storage_manager = AzureBlobStorageManager(os.environ["AZURE_STORAGE_DA_AGENT_CONTAINER"])
        token_counter = TokenCounter()
        self.db.initiate_blob_storage_manager_and_token_counter(
            blob_manager=self.azure_blob_storage_manager, token_counter=token_counter
        )
        # getting agent tools
        agent_tools, agent_tool_names = self._get_sqldb_tools()
        # Custom prompt template
        prompt = CustomPromptTemplate(
            template=sql_helper_prompt_template,
            tools=agent_tools,
            query_and_save_tool=agent_tools[-1].name,
            token_counter=token_counter,
            # This omits the `agent_scratchpad`, `tools`, and `tool_names` variables because those are generated dynamically
            # This includes the `intermediate_steps` variable because that is needed
            input_variables=["input", "intermediate_steps", "history", "message_id"],
        )
        # customr ouput parser
        output_parser = CustomOutputParser()
        # simple chain and single action agent
        llm_chain = LLMChain(llm=self.llm_chat_model, prompt=prompt)
        single_action_agent = LLMSingleActionAgent(
            llm_chain=llm_chain,
            output_parser=output_parser,
            stop=["\nObservation:"],
            allowed_tools=agent_tool_names,
        )
        message_history = AnalyticsAgentChatMessageHistory(chat_id=chat_id, db_session=db_session)
        memory = ConversationTokenBufferMemory(
            memory_key="history",
            chat_memory=message_history,
            llm=self.llm_chat_model,
            max_token=5000,
            output_key="output",
            input_key="input",
            return_messages=True,
        )

        self.agent_executor = AgentExecutor.from_agent_and_tools(
            agent=single_action_agent,
            tools=agent_tools,
            verbose=True,
            memory=memory,
            handle_parsing_errors=True
            # return_intermediate_steps=True,
        )

    def get_executor(self):
        return self.agent_executor

    def _get_sqldb_tools(self):
        toolkit = SQLDatabaseToolkit(db=self.db, llm=self.llm_chat_model, temperature=0)
        query_and_save_tool = QuerySaveSQLDataBaseTool(db=self.db)
        tools = toolkit.get_tools()
        tools.append(query_and_save_tool)
        tools[0].description = sql_db_query_description
        tools[1].description = sql_db_schema_description
        tool_names = [tool.name for tool in tools]

        return tools, tool_names

    async def invoke_async(self, user_query: str, message_id: UUID):
        is_agent_response_valid = True
        message_id_str = message_id.hex
        try:
            agent_response = await self.agent_executor.ainvoke({"input": user_query, "message_id": message_id_str})
            # deleting all files that are saved except the last one
            agent_response = self._delete_extra_csv_files(agent_response=agent_response, message_id=message_id)
            # adding sql markdown for the ones that do not have
            agent_response = self._add_sql_markdown(agent_response=agent_response, message_id=message_id)
        except Exception as e:
            print(f"Error during agent invocation: {e}")
            is_agent_response_valid = False
            agent_response = {"error": "Failed to process request"}

        return agent_response, is_agent_response_valid


    def _delete_extra_csv_files(self, agent_response: dict, message_id: UUID):
        if agent_response["stored_file_id"]:
            self.azure_blob_storage_manager.delete_extra_csv_files(
                message_id=message_id.hex, stored_file_id=agent_response["stored_file_id"]
            )
            agent_response["stored_file_id"] = f"{agent_response['message_id']}_{agent_response['stored_file_id']}.csv"
        return agent_response

    def _add_sql_markdown(self, agent_response: dict, message_id: UUID):
        if agent_response["sql_query"]:
            sql_query = agent_response["sql_query"]
            if not sql_query.startswith("```sql"):
                sql_markdown = f"```sql\n{sql_query}\n```"
                agent_response["sql_query"] = sql_markdown
        return agent_response


class AgentSnowflakeEngineManager:
    def __init__(self):
        self.engine = None

    def create_engine(self, snowflake_token: str, chat_obj: Chat):
        chat_snowflake_data_obj = chat_obj.snowflake_data

        # url = URL(
        #     user='jjabborov',
        #     password='newSecure1',
        #     account='CIPLNUD-YM27169',
        #     database="THREAD_SAMPLE",
        #     schema="PUBLIC", 
        #     warehouse='COMPUTE_WH',
        #     role = 'ACCOUNTADMIN'
        # )
        # engine = create_engine(url)
        
        snowflake_connection_url = "snowflake://{}/{}/{}?warehouse={}&authenticator=oauth&token={}".format(
            chat_snowflake_data_obj.snowflake_account,
            chat_snowflake_data_obj.database_name,
            chat_snowflake_data_obj.schema,
            chat_snowflake_data_obj.warehouse,
            urllib.parse.quote(snowflake_token),
        )
        engine = create_engine(snowflake_connection_url)
        try:
            con = engine.connect()
            con.close()
            self.engine = engine
            return True, ""

        except SQLAlchemyError as e:
            return False, f"{e.orig}"

    def is_engine_alive(self):
        if self.engine:
            try:
                # This is a simple way to check if the connection is alive
                with self.engine.connect():
                    return True
            except SQLAlchemyError:
                return False
        return False
