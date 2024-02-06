import re, json
from typing import Union
from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.exceptions import OutputParserException
from langchain.agents.agent import AgentOutputParser


class CustomJSONAgentOutputParser(AgentOutputParser):
    def parse_json_markdown(self, markdown_text):
        pattern = r"```json\n?(.*?)\n?```"
        match = re.search(pattern, markdown_text, re.DOTALL)

        if match:
            print(match.group(1), " group1")
            json_str = match.group(1)  # Extract the JSON string
            return json.loads(json_str)  # Parse and return the JSON object
        else:
            print("No JSON code block found.")
            return None

    def parse(self, text: str) -> Union[AgentAction, AgentFinish]:
        try:
            response = self.parse_json_markdown(text)
            print(response, " respon")
            if isinstance(response, list):
                # gpt turbo frequently ignores the directive to emit a single action
                response = response[0]
            if response["action"] == "Final Answer":
                document_searched_query = ""
                if "document_searched_query" in response.keys():
                    document_searched_query = response["document_searched_query"]
                return AgentFinish(
                    {"output": response["action_input"], "document_searched_query": document_searched_query}, text
                )
            else:
                return AgentAction(response["action"], response.get("action_input", {}), text)
        except Exception as e:
            raise OutputParserException(f"Could not parse LLM output: {text}") from e

    @property
    def _type(self) -> str:
        return "json-agent"
