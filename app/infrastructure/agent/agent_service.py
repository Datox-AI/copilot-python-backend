import urllib
from uuid import UUID
from typing import Dict
from dotenv import load_dotenv
from langchain.agents import AgentExecutor, LLMSingleActionAgent
from langchain.agents.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain.chains.llm import LLMChain
from langchain.memory import ConversationTokenBufferMemory
from langchain_community.chat_models import AzureChatOpenAI
from sqlalchemy.engine import create_engine
from sqlalchemy.engine.base import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.infrastructure.agent.agent_memory import CustomChatMessageHistory
from app.infrastructure.agent.azure_storage_manager import AzureBlobStorageManager
from app.infrastructure.agent.database_tools import CustomSQLDatabase, QuerySaveSQLDataBaseTool
from app.infrastructure.agent.token_counter import TokenCounter
from app.infrastructure.agent.output_parser import CustomOutputParser
from app.infrastructure.agent.prompt_template import CustomPromptTemplate
from app.infrastructure.agent.prompts.system_prompt import sql_helper_prompt_template
from app.infrastructure.agent.prompts.tool_prompts import sql_db_query_description, sql_db_schema_description

from app.models.maindb import Chat

load_dotenv()


class DataAnalyticAgent:
    def __init__(self, snowflake_engine: Engine, chat_id: UUID, db_session: Session):
        self.llm_chat_model = AzureChatOpenAI(deployment_name="gpt-4-32k", temperature=0)
        # initiating our db manager and assigning blob manager to our db
        self.db = CustomSQLDatabase(snowflake_engine, view_support=True)
        self.azure_blob_storage_manager = AzureBlobStorageManager()
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
        message_history = CustomChatMessageHistory(chat_id=chat_id, db_session=db_session)
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
            # return_intermediate_steps=True,
        )

    def _get_sqldb_tools(self):
        toolkit = SQLDatabaseToolkit(db=self.db, llm=self.llm_chat_model, temperature=0)
        query_and_save_tool = QuerySaveSQLDataBaseTool(db=self.db)
        tools = toolkit.get_tools()
        tools.append(query_and_save_tool)
        tools[0].description = sql_db_query_description
        tools[1].description = sql_db_schema_description
        tool_names = [tool.name for tool in tools]

        return tools, tool_names

    async def invoke(self, user_query: str, message_id: UUID):
        is_agent_response_valid = True
        message_id_str = message_id.hex
        agent_response = self.agent_executor.invoke({"input": user_query, "message_id": message_id_str})
        # deleting all files that are saved except the last one

        if agent_response["stored_file_id"] is not None:
            self.azure_blob_storage_manager.delete_extra_files(
                message_id=message_id_str, store_id=agent_response["stored_file_id"]
            )
            agent_response["stored_file_id"] = f"{agent_response['message_id']}_{agent_response['stored_file_id']}.csv"
            # is_agent_response_valid = False
            # agent_response = None

        return agent_response, is_agent_response_valid


class AgentSnowflakeEngineManager:
    
    def __init__(self):
        self.engine = None

    def create_engine(self, snowflake_token_data: Dict, chat_obj: Chat):
        if "oauth_token" not in snowflake_token_data:
            error_message = "Missing required 'oauth_token' value"
            return False, error_message 
        chat_snowflake_data_obj = chat_obj.snowflake_data

        snowflake_connection_url = "snowflake://{}/{}/{}?warehouse={}&authenticator=oauth&token={}".format(
            chat_snowflake_data_obj.snowflake_account,
            chat_snowflake_data_obj.database_name,
            chat_snowflake_data_obj.schema,
            chat_snowflake_data_obj.warehouse,
            urllib.parse.quote(snowflake_token_data["oauth_token"]),
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
