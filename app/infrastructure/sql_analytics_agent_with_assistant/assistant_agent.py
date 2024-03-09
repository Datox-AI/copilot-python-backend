# SQL_ASSISTANT_INSTRUCTIONS
import os
from uuid import UUID
from typing import Union
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from sqlalchemy.engine.base import Engine
from openai import AzureOpenAI, NotFoundError
from langchain.agents.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain.agents.openai_assistant import OpenAIAssistantRunnable
from langchain_core.agents import AgentFinish
from langchain_openai import AzureChatOpenAI

from app.infrastructure.sql_analytics_agent_with_assistant.sql_tool import CustomQuerySQLDataBaseTool
from app.infrastructure.analytics_agent.database_tools import CustomSQLDatabase
from app.infrastructure.analytics_agent.azure_storage_manager import AzureBlobStorageManager
from app.infrastructure.analytics_agent.token_counter import TokenCounter
from app.infrastructure.sql_analytics_agent_with_assistant.prompts import SQL_ASSISTANT_INSTRUCTIONS


load_dotenv()


class DataAnalyticAssistant:
    
    def __init__(self, snowflake_engine: Engine, thread_id: Union[str, None]):
        self.llm_chat_model = AzureChatOpenAI(
            deployment_name=os.getenv("GPT4_TURBO_DEPLOYMENT_NAME"),
            azure_endpoint=os.getenv("GPT4_TURBO_AZURE_OPENAI_ENDPOINT"),
            openai_api_version=os.getenv("GPT4_TURBO_OPENAI_API_VERSION"),
            openai_api_key=os.getenv("GPT4_TURBO_AZURE_OPENAI_API_KEY"),
            temperature=0,
            streaming=True,
        )
        
        self.client = AzureOpenAI(
            api_key=os.getenv("GPT4_TURBO_AZURE_OPENAI_API_KEY"),  
            api_version=os.getenv("GPT4_ASSISTANT_OPENAI_API_VERSION"),
            azure_endpoint=os.getenv("GPT4_TURBO_AZURE_OPENAI_ENDPOINT")
        )
        self.db = CustomSQLDatabase(snowflake_engine, view_support=True)
        container_name = os.getenv("AZURE_STORAGE_DA_ASSISTANT_AGENT_CONTAINER", "assistant-agent-intermediate-steps-files")
        
        
        azure_blob_storage_manager = AzureBlobStorageManager(
            container_name
        )
        token_counter = TokenCounter()

        self.db.initiate_blob_storage_manager_and_token_counter(
            blob_manager=azure_blob_storage_manager,
            token_counter=token_counter
        )
        # getting necessary tools 
        self.sql_tools = self._get_sqldb_tools()
        # getting assistant and thread
        assistant_id = os.getenv("SQL_ANALYTIC_AZURE_ASSISTANT_ID")
        my_assistant = self.client.beta.assistants.retrieve(assistant_id)
        if thread_id:    
            self.thread_id = thread_id        
            self.client.beta.threads.retrieve(thread_id=thread_id)
        else:
            empty_thread = self.client.beta.threads.create()
            self.thread_id = empty_thread.id
        
        self.agent = OpenAIAssistantRunnable(
            assistant_id=assistant_id,
            client=self.client, 
            as_agent=True
        )
    

    def execute_agent(self, input: str, message_id: UUID):
        generated_query = None
        stored_id = None
        tool_map = {tool.name: tool for tool in self.sql_tools}
        response = self.agent.invoke(input={
            "content": input,
            "thread_id": self.thread_id
        })
        while not isinstance(response, AgentFinish):
            tool_outputs = []
            thread_id = response[0].thread_id
            run_id = response[0].run_id
            try:
                print(response, " ---response")
                for action in response:
                    if action.tool == "sql_db_query":
                        generated_query = action.tool_input
                        tool_response = tool_map[action.tool].invoke(input={
                            "query": action.tool_input,
                            "message_id": message_id.hex
                        })
                        if type(tool_response) == dict:
                            tool_output = tool_response["res"]
                            stored_id = tool_response["stored_file_id"]
                        else:
                            tool_output = tool_response
                    else:
                        tool_output = tool_map[action.tool].invoke(action.tool_input)
                    
                    print(action.tool, action.tool_input, tool_output, end="\n\n")
                    tool_outputs.append(
                        {"output": tool_output, "tool_call_id": action.tool_call_id}
                    )
                response = self.agent.invoke(
                    {
                        "tool_outputs": tool_outputs,
                        "run_id": action.run_id,
                        "thread_id": action.thread_id,
                    }
                )
            except Exception as e:
                try:
                    self.client.beta.threads.runs.cancel(
                        thread_id=thread_id,
                        run_id=run_id
                    )
                    print("cancenlled")
                except:
                    print("nahh")
                    pass
                finally:
                    return f"Agent failed: {e}"
                
        return {
            "output": response.return_values["output"],
            "thread_id": response.return_values["thread_id"],
            "sql_query": generated_query,
            "stored_file_id": stored_id
        }
               
    
    def _get_sqldb_tools(self):
        toolkit = SQLDatabaseToolkit(db=self.db, llm=self.llm_chat_model, temperature=0)
        sql_db_query_tool = CustomQuerySQLDataBaseTool(db=self.db)
        tools = toolkit.get_tools()[1:-1]
        tools.append(sql_db_query_tool)
        tool_names = [tool.name for tool in tools]

        return tools

        
