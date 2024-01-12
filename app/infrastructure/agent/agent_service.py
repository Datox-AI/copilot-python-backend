from langchain.agents import Tool, AgentExecutor, LLMSingleActionAgent
from langchain.chains.llm import LLMChain
from langchain_community.chat_models import AzureChatOpenAI
from langchain.agents.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain.memory import ConversationTokenBufferMemory
# from langchain.memory.chat_message_histories import StreamlitChatMessageHistory
from langchain.agents.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
import os 
from dotenv import load_dotenv
from sqlalchemy.engine.base import Engine
from sqlalchemy.engine import create_engine
from sqlalchemy.exc import SQLAlchemyError
import urllib

from app.infrastructure.agent.prompts.system_prompt import sql_helper_prompt_template
from app.infrastructure.agent.prompts.tool_prompts import  sql_db_query_description, sql_db_schema_description
from app.infrastructure.agent.database_tools import QuerySaveSQLDataBaseTool, CustomSQLDatabase
from app.infrastructure.agent.prompt_template import CustomPromptTemplate
from app.infrastructure.agent.output_parser import CustomOutputParser
from app.infrastructure.agent.helpers import count_tokens
from sqlalchemy.engine import Engine

load_dotenv()
# os.environ[""]

# os.environ["OPENAI_API_TYPE"] = config("OPENAI_API_TYPE")
# os.environ["OPENAI_API_BASE"] = config("OPENAI_API_BASE")
# os.environ["OPENAI_API_VERSION"] = config("OPENAI_API_VERSION")
# os.environ["OPENAI_API_KEY"] = config("OPENAI_API_KEY")


class DataAnalyticAgent:

    def __init__(self, engine: Engine):
        self.llm_chat_model = AzureChatOpenAI(
            deployment_name="gpt-4-32k", 
            temperature=0
        )
        self.db = CustomSQLDatabase(engine, view_support=True)
        # getting agent tools
        agent_tools, agent_tool_names = self._get_sqldb_tools()
        # Custom prompt template
        prompt = CustomPromptTemplate(
            template=sql_helper_prompt_template,
            tools=agent_tools,
            query_and_save_tool=agent_tools[-1].name,
            # This omits the `agent_scratchpad`, `tools`, and `tool_names` variables because those are generated dynamically
            # This includes the `intermediate_steps` variable because that is needed
            input_variables=["input", "intermediate_steps", "history", "message_id"]
        )
        # customr ouput parser
        output_parser = CustomOutputParser()
        # simple chain and single action agent 
        llm_chain = LLMChain(llm=self.llm_chat_model, prompt=prompt)
        single_action_agent = LLMSingleActionAgent(
            llm_chain=llm_chain,
            output_parser=output_parser,
            stop=["\nObservation:"],
            allowed_tools=agent_tool_names
        )    
        memory = ConversationTokenBufferMemory(
            memory_key="history",
            # chat_memory=message_history,
            llm=self.llm_chat_model,
            max_token=5000, 
            output_key="output", 
            input_key="input",
            return_messages=True
        )

        self.agent_executor = AgentExecutor.from_agent_and_tools(
            agent=single_action_agent, 
            tools=agent_tools, 
            verbose=True, 
            memory=memory,
            return_intermediate_steps=True
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

        
    async def invoke(self, user_query):
        agent_response = self.agent_executor.invoke(
            {
                "input": user_query,
                "message_id": "test"
            }
        )
        return agent_response


class AgentEngine:
    def __init__(self, snowlfake_account: str, db_name: str, scheme: str, warehouse: str, oauth_token: str):
        parsed_token = urllib.parse.quote(oauth_token)
        snowflake_connection_url = "snowflake://{}/{}/{}?warehouse={}&authenticator=oauth&token={}".format(
            snowlfake_account,
            db_name,
            scheme,
            warehouse,
            parsed_token
        )

        # setting up database connection with Snowflake
        engine = create_engine(snowflake_connection_url)
        try:
            con = engine.connect()
            con.close()
        except SQLAlchemyError as e:
            raise e