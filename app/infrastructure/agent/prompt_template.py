from langchain.prompts import BaseChatPromptTemplate
from langchain.schema import SystemMessage
from langchain.tools import BaseTool
from typing import List
from app.infrastructure.agent.helpers import count_tokens


# Set up a prompt template
class CustomPromptTemplate(BaseChatPromptTemplate):
    # The template to use
    template: str
    # The list of tools available
    tools: List[BaseTool]
    query_and_save_tool: str

    def format_messages(self, **kwargs) -> str:
        # Get the intermediate steps (AgentAction, Observation tuples)
        # Format them in a particular way
        # addding file_path
        history_text = ""
        if "history" in kwargs:
            history_messages = kwargs.pop("history")
            for history_message in history_messages:
                history_text += f"{history_message.type}: {history_message.content}\n"
            kwargs["history"] = history_text

        intermediate_steps = kwargs.pop("intermediate_steps")
        thoughts = ""
        for action, observation in intermediate_steps:
            thoughts += action.log
            thoughts += f"\nObservation: {observation}\nThought: "
        # Set the agent_scratchpad variable to that value
        kwargs["agent_scratchpad"] = thoughts
        # Create a tools variable from the list of tools provided
        kwargs["tools"] = "\n\n".join(
            [f"{tool.name}: {tool.description}" for tool in self.tools]
        )
        kwargs["query_and_save_tool"] = self.query_and_save_tool
        # Create a list of tool names for the tools provided
        kwargs["tool_names"] = ", ".join([tool.name for tool in self.tools])
        formatted = self.template.format(**kwargs)
        # counting tokens
        # record_token_record(reset=True)
        print(formatted, " formatted")
        count_tokens(input=formatted, agent_step="Prompting")
        return [SystemMessage(content=formatted)]
