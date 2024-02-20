import ast
import re
from typing import List

from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.output_parsers import JsonOutputParser
from langchain.agents import AgentOutputParser
from langchain.schema import AgentAction, AgentFinish


# Final answer output parser 
class FinalAnswer(BaseModel):
    final_output: str = Field(description="Final answer and insights to the original input question")
    confirmation: str = Field(description="Confirmation to move on the next query if there is more than one query")
    stored_file_id: str = Field(description="Stored ID of the result from sql query")
    sql_query: str = Field(description="SQL query you generated to get the final answer")
    followup_questions: List[str] = "Followup questions user might want to ask about the table you used"


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
            if "stored_file_id" in parsed_data.keys() and parsed_data["stored_file_id"] == "":
                parsed_data["stored_file_id"] = None        
            if "sql_query" in parsed_data.keys() and parsed_data["sql_query"] == "":
                parsed_data["sql_query"] = None
    
            return AgentFinish(
                # Return values is generally always a dictionary with a single `output` key
                # It is not recommended to try anything else at the moment :)
                ## Fuck the recommendation above, bois, we ball.
                return_values={
                    "output": parsed_data["final_output"], 
                    "confirmation": parsed_data["confirmation"] if "confirmation" in parsed_data.keys() else None, 
                    "stored_file_id": parsed_data["stored_file_id"],
                    "sql_query": parsed_data["sql_query"],
                    "followup_questions": parsed_data["followup_questions"] if "followup_questions" in parsed_data.keys() else None,

                },
                log=llm_output,
            )
        # Parse out the action and action input
        regex = r"Action\s*\d*\s*:(.*?)\nAction\s*\d*\s*Input\s*\d*\s*:[\s]*(.*)"
        # regex = r"Action\s*\d*\s*:(.*?)\nAction\s*\d*\s*Input\s*\d*\s*:[\s]*(.*?)(?:\nMessage ID:\s*(.*?))?$"

        match = re.search(regex, llm_output, re.DOTALL)
        if not match:
            raise ValueError(f"Could not parse LLM output: `{llm_output}`")
        action = match.group(1).strip()
        action_input = match.group(2).strip(" ").strip('"')

        # Return the action and action input
        if action == "sql_db_query_save":
            tool_input = ast.literal_eval(action_input)
        else:
            tool_input = action_input
        return AgentAction(tool=action, tool_input=tool_input, log=llm_output)
