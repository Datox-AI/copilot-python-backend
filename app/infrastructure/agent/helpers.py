from langchain.agents.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from app.infrastructure.agent.prompts.tool_prompts import sql_db_query_description, sql_db_schema_description


def count_tokens(input: str, agent_step: str | None = None):
    return True 