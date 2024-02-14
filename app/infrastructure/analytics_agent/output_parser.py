import ast
import re
from typing import Union

from langchain.agents import AgentOutputParser
from langchain.schema import AgentAction, AgentFinish


class CustomOutputParser(AgentOutputParser):
    def parse(self, llm_output: str) -> AgentAction | AgentFinish:
        # count_tokens(input=llm_output, agent_step="final output")

        # Check if agent should finish
        # if "Observation:" in llm_output:
        # observation_text = llm_output.split("Observation:")[-1].strip().split("Final Answer")[0]
        if "Final Answer: " in llm_output:
            final_answer_pattern = (
                r"Final Answer: (.*?)(?:Stored ID: (.*?))?(?:\nSQL query:(.*?))?(?:\nFollowup Questions:(.*))?$"
            )

            matches = re.search(final_answer_pattern, llm_output, re.DOTALL)
            final_answer = matches.group(1).strip()
            stored_file_id = matches.group(2).strip() if matches.group(2) else None
            sql_query = matches.group(3).strip() if matches.group(3) else None
            followup_questions_text = matches.group(4).strip() if matches.group(4) else None
            if followup_questions_text:
                followup_questions = followup_questions_text.split("\n")
            else:
                followup_questions = None

            return AgentFinish(
                # Return values is generally always a dictionary with a single `output` key
                # It is not recommended to try anything else at the moment :)
                return_values={
                    "output": final_answer,
                    "sql_query": sql_query,
                    "stored_file_id": stored_file_id,
                    "followup_questions": followup_questions,
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
