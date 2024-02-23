import ast
import re
from typing import List, Union

from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.output_parsers import JsonOutputParser
from langchain.agents import AgentOutputParser
from langchain.schema import AgentAction, AgentFinish


# Final answer output parser
class FinalAnswer(BaseModel):
    output: str = Field(description="Final answer and insights to the original input question")
    confirmation: Union[str, None] = Field(
        description="the confirmation to move on the next query if there is more than one query"
    )
    stored_file_id: str = Field(description="Stored ID of the result from sql query")
    sql_query: str = Field(description="SQL query you generated to get the final answer")
    followup_questions: List[str] = "Followup questions user might want to ask about the table you used"
    choices: List[str] = "choices that might be available for user to select"


class CustomOutputParser(AgentOutputParser):
    parser = JsonOutputParser(pydantic_object=FinalAnswer)

    def parse(self, llm_output: str) -> AgentAction | AgentFinish:
        # count_tokens(input=llm_output, agent_step="final output")

        # Check if agent should finish
        # if "Observation:" in llm_output:
        # observation_text = llm_output.split("Observation:")[-1].strip().split("Final Answer")[0]
        if "Final Answer:" in llm_output:
            final_answer = llm_output.split("Final Answer:")[1]
            parsed_data = self.parser.parse(final_answer)
            # converting from empty string to None
            empty_str_to_none_list = ["stored_file_id", "sql_query", "confirmation"]
            for empty_str_field in empty_str_to_none_list:
                if empty_str_field in parsed_data.keys():
                    if parsed_data[empty_str_field] == "":
                        parsed_data[empty_str_field] = None
                else:
                    parsed_data[empty_str_field] = None
            # converting from none to empty list
            none_to_empty_list = ["followup_questions", "choices"]
            for none_field in none_to_empty_list:
                if none_field not in parsed_data.keys():
                    parsed_data[none_field] = []
            # adding confirmation to the output
            if "confirmation" in parsed_data.keys() and parsed_data["confirmation"] is not None:
                parsed_data["output"] = "{}\n\n{}".format(parsed_data["output"], parsed_data["confirmation"])
            return AgentFinish(
                # Return values is generally always a dictionary with a single `output` key
                # It is not recommended to try anything else at the moment :)
                ## Fuck the recommendation above, bois. we ball
                return_values={**parsed_data},
                log=llm_output,
            )
        # Parse out the action and action input
        regex = r"Action\s*\d*\s*:(.*?)\nAction\s*\d*\s*Input\s*\d*\s*:[\s]*(.*)"
        match = re.search(regex, llm_output, re.DOTALL)
        if not match:
            raise ValueError(f"Could not parse LLM output: `{llm_output}`")
        action = match.group(1).strip()
        action_input = match.group(2).strip(" ").strip('"')

        # Return the action and action input
        if action == "sql_db_query_save":
            # converting input to dict value
            tool_input = ast.literal_eval(action_input)
        else:
            tool_input = action_input
        return AgentAction(tool=action, tool_input=tool_input, log=llm_output)
