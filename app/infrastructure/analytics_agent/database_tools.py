from typing import Literal

import pandas as pd
from langchain.tools.sql_database.tool import QuerySQLDataBaseTool
from langchain.utilities.sql_database import truncate_word
from langchain_community.utilities import SQLDatabase
from sqlalchemy.exc import SQLAlchemyError

from app.infrastructure.analytics_agent.azure_storage_manager import AzureBlobStorageManager
from app.infrastructure.analytics_agent.token_counter import TokenCounter
from app.infrastructure.analytics_agent.prompts.tool_prompts import query_and_save_tool_description


class CustomSQLDatabase(SQLDatabase):
    def initiate_blob_storage_manager_and_token_counter(
        self, blob_manager: AzureBlobStorageManager, token_counter: TokenCounter
    ):
        # it is just preventing from initiating blob manager over and over. Make sure to run this before running the agent
        # and I added token counter to the same method
        self.blob_manager = blob_manager
        self.token_counter = token_counter

    def run_and_save(
        self,
        command: str,
        message_id: str,
        fetch="all",
    ) -> str:
        """Execute a SQL command, save the result and return a string representing the results and stored_file_id.

        If the statement returns rows, a string of the results is returned.
        If the statement returns no rows, an empty string is returned.
        """
        result = self._execute(command, fetch)
        # uploading the result
        df = pd.DataFrame(result)
        stored_file_id = self.blob_manager.upload_csv(df=df, message_id=message_id)
        # Convert columns values to string to avoid issues with sqlalchemy
        # truncating text
        res = [tuple(truncate_word(c, length=self._max_string_length) for c in r.values()) for r in result]
        if not res:
            return ""
        else:
            if not self.token_counter.count_tokens(input=str(res), agent_step="sql_query_run"):
                first_ten_rows = result[:10]
                res = [
                    tuple(truncate_word(c, length=self._max_string_length) for c in r.values()) for r in first_ten_rows
                ]
                return f"Token overloaded.\nFirst 10 rows of data: {res}\nStored ID: {stored_file_id}"

            return f"Data: {res}\nStored ID: {stored_file_id}"

    def run_and_save_no_throw(
        self,
        command: str,
        message_id: str,
        fetch: Literal["all"] | Literal["one"] = "all",
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
        run_manager=None,
    ) -> str:
        """Execute the query, return the results with stored id, or an error message."""
        return self.db.run_and_save_no_throw(query, message_id)
