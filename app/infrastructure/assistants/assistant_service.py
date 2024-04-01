import os, json
from typing import List
from uuid import UUID
from dotenv import load_dotenv
from openai import AzureOpenAI
from fastapi import HTTPException
from langchain.agents.openai_assistant import OpenAIAssistantRunnable
from langchain_core.agents import AgentFinish
from langchain_openai import AzureChatOpenAI

from app.infrastructure.assistants.tool import get_documents
from app.infrastructure.ChatGPT_assistant.prompt import FOLLOWUP_QUESTIONS_PROMPT


load_dotenv(override=True)


class AssistantAgent:
    def __init__(self, assistant_id, thread_id):
        self.llm_chat_model = AzureChatOpenAI(
            deployment_name=os.getenv("GPT4_TURBO_DEPLOYMENT_NAME"),
            azure_endpoint=os.getenv("GPT4_TURBO_AZURE_OPENAI_ENDPOINT"),
            openai_api_version=os.getenv("GPT4_TURBO_OPENAI_API_VERSION"),
            openai_api_key=os.getenv("GPT4_TURBO_AZURE_OPENAI_API_KEY"),
            temperature=0,
            streaming=True,
        )
        self.client = AzureOpenAI(
            azure_endpoint=os.environ.get("GPT4_TURBO_AZURE_OPENAI_ENDPOINT"),
            api_key=os.environ.get("GPT4_TURBO_AZURE_OPENAI_API_KEY"),
            api_version=os.environ.get("GPT4_ASSISTANT_OPENAI_API_VERSION"),
        )
        self.tools = [get_documents]
        print(assistant_id, " -eeee")
        try:
            self.client.beta.assistants.retrieve(assistant_id=assistant_id)
        except Exception as e:
            print(f"Assistant not found in azure: {e}")
            raise HTTPException(detail=f"Assistant (id={assistant_id}) not found in azure", status_code=404)
        try:
            self.client.beta.threads.retrieve(thread_id=thread_id)
        except Exception as e:
            print(f"Thread not found: {e}")
            raise HTTPException(detail=f"Thread (id={thread_id}) not found", status_code=404)

        self.thread_id = thread_id
        self.agent = OpenAIAssistantRunnable(assistant_id=assistant_id, client=self.client, as_agent=True)

    def execute_agent(
        self,
        user_input: str,
        knowledge_files_ids: List[UUID],
    ):
        tool_map = {tool.name: tool for tool in self.tools}
        response = self.agent.invoke(input={"content": user_input, "thread_id": self.thread_id})
        relevant_docs = []
        while not isinstance(response, AgentFinish):
            tool_outputs = []
            run_id = response[0].run_id
            try:
                for action in response:
                    tool_input = action.tool_input
                    # adding user input if assistant misses to add query inside input
                    tool_input.update({"knowledge_files_ids": knowledge_files_ids})
                    tool_output, relevant_docs = tool_map[action.tool].invoke(tool_input)
                    tool_outputs.append({"output": tool_output, "tool_call_id": action.tool_call_id})
                response = self.agent.invoke(
                    {
                        "tool_outputs": tool_outputs,
                        "run_id": action.run_id,
                        "thread_id": action.thread_id,
                    }
                )
            except Exception as e:
                try:
                    self.client.beta.threads.runs.cancel(thread_id=self.thread_id, run_id=run_id)
                    print("cancelled")
                except:
                    print("nahh")
                    pass
                finally:
                    raise HTTPException(status_code=500, detail=f"Agent failed: {e}")

        # followup_questions = self.generate_followup_questions(
        #     question=input,
        #     answer=response.return_values["output"]
        # )
        followup_questions = []

        return {
            "output": response.return_values["output"],
            "thread_id": response.return_values["thread_id"],
            "relevant_docs": relevant_docs,
            "followup_questions": followup_questions,
        }

    def generate_followup_questions(self, question: str, answer: str):
        prompt = FOLLOWUP_QUESTIONS_PROMPT.format(question=question, answer=answer)

        followup_questions_str = self.llm_chat_model.invoke(prompt)
        print(followup_questions_str)
        try:
            followup_questions = json.loads(followup_questions_str.content)
            return followup_questions["questions_answers"]
        except:
            return []
