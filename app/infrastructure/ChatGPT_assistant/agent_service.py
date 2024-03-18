import os, json
from typing import Union, List
from uuid import UUID
from dotenv import load_dotenv
from openai import AzureOpenAI
from langchain.tools import tool
from langchain.agents.openai_assistant import OpenAIAssistantRunnable
from langchain_core.agents import AgentFinish
from langchain_openai import AzureChatOpenAI
from azure.search.documents.models import VectorFilterMode, VectorizedQuery
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from app.infrastructure.ChatGPT_assistant.prompt import FOLLOWUP_QUESTIONS_PROMPT


load_dotenv()

openai_client = AzureOpenAI(
    azure_endpoint=os.environ.get("GPT4_TURBO_AZURE_OPENAI_ENDPOINT"),
    api_key=os.environ.get("GPT4_TURBO_AZURE_OPENAI_API_KEY"),
    api_version=os.environ.get("GPT4_TURBO_OPENAI_API_VERSION"),
)

search_client = SearchClient(
    endpoint=os.environ.get("AZURE_COGNITIVE_SEARCH_INDEX_URL"),
    index_name=os.environ.get("AZURE_COGNITIVE_SEARCH_CHATGPT_INDEX_NAME"),
    credential=AzureKeyCredential(os.environ.get("AZURE_COGNITIVE_SEARCH_API_KEY")),
)


@tool
def get_documents(query: str, user_id: str, chat_id: str, file_id: str = None):
    """this tool is for getting relevant context for user's question.Input to this is user's question and output is necessary context for that question"""
    print(user_id, " user_id=")
    print(chat_id, " chat_id=")

    response = openai_client.embeddings.create(input=query, model=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME"))
    embedding = response.data[0].embedding
    vector_query = VectorizedQuery(vector=embedding, k_nearest_neighbors=3, fields="contentVector")
    if file_id:
        filter = f"chatId eq '{chat_id}' and fileId eq '{file_id}'"
    else:
        filter = f"chatId eq '{chat_id}'"

    results = search_client.search(
        search_text=None,
        vector_queries=[vector_query],
        vector_filter_mode=VectorFilterMode.PRE_FILTER,
        filter=filter,
        select=["content", "file_type", "fileId", "chatId"],
    )
    text_content = ""
    for result in results:
        text_content += f"{result['content']}"
    print(text_content, " content")
    return text_content


class ChatGPTAssistant:
    def __init__(self, thread_id):
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
        assistant_id = os.getenv("CHATGPT_AGENT_AZURE_ASSISTANT_ID")
        print(assistant_id, " -eeee")
        my_assistant = self.client.beta.assistants.retrieve(assistant_id=assistant_id)
        if thread_id:
            self.thread_id = thread_id
            self.client.beta.threads.retrieve(thread_id=thread_id)
        else:
            empty_thread = self.client.beta.threads.create()
            self.thread_id = empty_thread.id

        self.agent = OpenAIAssistantRunnable(assistant_id=assistant_id, client=self.client, as_agent=True)

    def execute_agent(
        self,
        user_input: str,
        user_id: UUID,
        chat_id: UUID,
        file_ids: List[Union[UUID, None]] = None,
    ):

        tool_map = {tool.name: tool for tool in self.tools}
        response = self.agent.invoke(input={"content": user_input, "thread_id": self.thread_id})
        while not isinstance(response, AgentFinish):
            tool_outputs = []
            run_id = response[0].run_id
            try:
                for action in response:

                    tool_input = action.tool_input
                    # adding user input if assistant misses to add query inside input
                    if "query" not in tool_input.keys():
                        print("manually updating query")
                        tool_input["query"] = user_input
                    tool_input.update({"user_id": str(user_id), "chat_id": str(chat_id)})
                    tool_output = tool_map[action.tool].invoke(tool_input)
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
                    print("cancenlled")
                except:
                    print("nahh")
                    pass
                finally:
                    return f"Agent failed: {e}"

        # followup_questions = self.generate_followup_questions(
        #     question=input,
        #     answer=response.return_values["output"]
        # )
        followup_questions = []
        print(followup_questions, "-----folowwup")
        return {
            "output": response.return_values["output"],
            "thread_id": response.return_values["thread_id"],
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
