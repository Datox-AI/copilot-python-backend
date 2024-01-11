from langchain_community.utilities import SQLDatabase
from langchain.utilities.sql_database import truncate_word
from langchain.tools.sql_database.tool import QuerySQLDataBaseTool
from sqlalchemy.exc import SQLAlchemyError
import pandas as pd 
from typing import Union, Literal
import random, string, os, tiktoken, time
from app.infrastructure.agent.helpers import count_tokens
from app.infrastructure.agent.prompts.tool_prompts import query_and_save_tool_description



class CustomSQLDatabase(SQLDatabase):

    def run_and_save(
        self,
        command: str,
        message_id: str, 
        fetch = "all",
    ) -> str:
        """Execute a SQL command, save the result and return a string representing the results and stored_id.

        If the statement returns rows, a string of the results is returned.
        If the statement returns no rows, an empty string is returned.
        """
        result = self._execute(command, fetch)
        # generating file path with random string 
        random_string = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(15))
        message_folder_path = os.path.join("stored_data", message_id)
        if not os.path.exists(message_folder_path):
            os.mkdir(message_folder_path)
        full_file_path = os.path.join(message_folder_path, f"{random_string}.csv")
        # saving the result
        pd.DataFrame(result).to_csv(full_file_path, index=False)
        
        # Convert columns values to string to avoid issues with sqlalchemy
        # truncating text
        res = [
            tuple(truncate_word(c, length=self._max_string_length) for c in r.values())
            for r in result
        ]
        if not res:
            return ""
        else:
            if not count_tokens(input=str(res), agent_step="query_run"):
                first_ten_rows = result[:10]
                res = [
                    tuple(truncate_word(c, length=self._max_string_length) for c in r.values())
                    for r in first_ten_rows
                ]
                return f"Token overloaded.\nFirst 10 rows of data: {res}\nStored ID: {random_string}"
            
            return f"Data: {res}\nStored ID: {random_string}"


    def run_and_save_no_throw(
        self,
        command: str,
        message_id: str,
        fetch: Union[Literal["all"], Literal["one"]] = "all",
    ) -> str:
        """Execute a SQL command and return a string representing the results.

        If the statement returns rows, a string of the results is returned.
        If the statement returns no rows, an empty string is returned.

        If the statement throws an error, the error message is returned.
        """
        try:
            return self.run_and_save(command, message_id, fetch)
        except SQLAlchemyError as e:
            """Format the error message"""
            return f"Error: {e}"
        

# run and save tool
class QuerySaveSQLDataBaseTool(QuerySQLDataBaseTool):
    name: str = "sql_db_query_save"
    description: str = query_and_save_tool_description

    def _run(
        self,
        query: str,
        message_id: str,
        run_manager = None,
    ) -> str:
        """Execute the query, return the results with stored id, or an error message."""
        return self.db.run_and_save_no_throw(query, message_id)