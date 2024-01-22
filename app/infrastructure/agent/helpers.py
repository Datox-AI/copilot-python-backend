import tiktoken
from langchain.agents.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from app.infrastructure.agent.prompts.tool_prompts import (
    sql_db_query_description,
    sql_db_schema_description,
)


class TokenCounter:
    def __init__(self, max_token: int = 32768):
        # gpt encoding
        self.enc = tiktoken.get_encoding("cl100k_base")
        self.max_token = max_token
        self.current_left_token = self.max_token

    def count_tokens(self, input: str, agent_step: str):
        if agent_step == "prompting":
            self.current_left_token = self.max_token
        tokens = self.enc.encode(input)
        print(len(tokens), " used token number")
        if len(tokens) >= self.current_left_token:
            return False
        elif agent_step == "sql_query_run" and len(tokens) >= 5000:
            return False
        else:
            self.current_left_token = self.current_left_token - len(tokens)
            print(self.current_left_token, " left token number")
            return True
