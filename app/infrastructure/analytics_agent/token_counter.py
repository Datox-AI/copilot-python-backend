import tiktoken


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

    def over_limit(self, input: str):
        tokens = self.enc.encode(input)
        if len(tokens) > 500:
            return True
        return False
