from langchain.tools.sql_database.tool import QuerySQLDataBaseTool
from langchain_community.utilities import SQLDatabase

from app.infrastructure.sql_analytics_agent_with_assistant.prompts import db_query_tool_description
from app.infrastructure.analytics_agent.agent_service import CustomSQLDatabase



class CustomQuerySQLDataBaseTool(QuerySQLDataBaseTool):
    name: str = "sql_db_query"
    description: str = db_query_tool_description

    def _run(
        self,
        query: str,
        message_id: str,
        run_manager=None,
    ) -> str:
        """Execute the query, return the results with stored id, or an error message."""
        return self.db.run_and_no_throw_for_assistant(query, message_id)
