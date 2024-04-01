import sqlparse
from langchain.tools.sql_database.tool import QuerySQLDataBaseTool
from langchain_community.utilities import SQLDatabase

from app.infrastructure.sql_analytics_agent_with_assistant.prompts import db_query_tool_description
from app.infrastructure.analytics_agent.agent_service import CustomSQLDatabase


forbidden_keywords = [
    "alter",
    "drop",
    "modify",
    "create",
    "create or replace",
    "insert",
    "delete",
    "update",
    "truncate",
    "rename",
]


def is_query_allowed(sql_query):
    parsed = sqlparse.parse(sql_query)[0]
    tokens = [token for token in parsed.tokens if not token.is_whitespace]
    print(tokens, " token")
    for token in tokens:
        if token.ttype is sqlparse.tokens.DDL or token.ttype is sqlparse.tokens.DML:
            for keyword in forbidden_keywords:
                if keyword.upper() == token.value.upper():
                    return False
    return True


class CustomQuerySQLDataBaseTool(QuerySQLDataBaseTool):
    name: str = "sql_db_query"
    description: str = db_query_tool_description

    def _run(
        self,
        query: str,
        message_id: str,
        run_manager=None,
    ) -> str:
        print(query, " query")
        if is_query_allowed(query):
            print("IT is trueeee")
            """Execute the query, return the results with stored id, or an error message."""
            return self.db.run_and_no_throw_for_assistant(query, message_id)
        else:
            print("IT is nott")
            return "This query cannot be runned since it contains DML or DDL statement"
