import os
import json
from uuid import UUID
from typing import Union

from dotenv import load_dotenv
from langchain.tools import tool
from langchain.agents.openai_assistant import OpenAIAssistantRunnable
from langchain_core.agents import AgentFinish

from sqlalchemy.orm import Session
from openai import AzureOpenAI
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery

from app.infrastructure.RAG_agent.prompts.system_prompt import (
    SYSTEM_MESSAGE_TEMPLATE,
)

load_dotenv(override=True)
THRESHOLD = 0.3
TOP_K = 5


@tool
def get_documents(prompt):
    """This tool for get relevant documents from sharepoint"""
    print(prompt, "---prompt")
    relevant_docs = get_documents_from_azure_search(user_query=prompt, search_type="hybrid")
    final_docs_content = ""
    for doc in relevant_docs:
        final_docs_content = (
            final_docs_content + f"FILE NAME: {doc['metadata_spo_item_name']}\nFILE CONTENT: {doc['content']}\n\n"
        )
    return final_docs_content, relevant_docs


def filter_data_by_reranker_score(data, difference_threshold=0.5):
    """
    Filters a list of numbers by removing all elements after finding a difference greater or equal to 'difference_threshold' between consecutive numbers.

    :param numbers: List of numbers to be filtered.
    :param difference_threshold: Threshold value for the difference to trigger filtering.
    :return: Filtered list of numbers.
    """
    filtered_data = []
    for i in range(len(data) - 1):
        current_score = data[i].get("@search.reranker_score", 0)
        next_score = data[i + 1].get("@search.reranker_score", 0)

        filtered_data.append(data[i])
        if next_score == None:
            break
        if abs(current_score - next_score) >= difference_threshold:
            break
    if TOP_K:
        return filtered_data[:TOP_K]
    return filtered_data


def get_embeddings(text: str):
    # There are a few ways to get embeddings. This is just one example.
    import openai

    open_ai_endpoint = os.getenv("GPT4_TURBO_AZURE_OPENAI_ENDPOINT")
    open_ai_key = os.getenv("GPT4_TURBO_AZURE_OPENAI_API_KEY")

    client = openai.AzureOpenAI(
        azure_endpoint=open_ai_endpoint,
        api_key=open_ai_key,
        api_version="2023-08-01-preview",
    )
    embedding = client.embeddings.create(input=[text], model=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME"))
    return embedding.data[0].embedding


def get_documents_from_azure_search(user_query: str, search_type: str):
    credential = AzureKeyCredential(os.getenv("AZURE_COGNITIVE_SEARCH_API_KEY"))
    azure_client = SearchClient(
        endpoint=os.getenv("AZURE_COGNITIVE_SEARCH_INDEX_URL"),
        index_name=os.getenv("AZURE_COGNITIVE_SEARCH_SHAREPOINT_INDEX_NAME"),
        credential=credential,
    )
    if search_type == "hybrid":
        vector_query = VectorizedQuery(
            vector=get_embeddings(user_query),
            k_nearest_neighbors=TOP_K,
            fields="contentVector",
        )

        search_result = azure_client.search(
            vector_queries=[vector_query],
            select=[
                "id",
                "content",
                "metadata_spo_item_name",
                "metadata_spo_item_path",
                "metadata_spo_item_content_type",
                "metadata_spo_item_last_modified",
                "metadata_spo_item_size",
                "metadata_spo_item_weburi",
            ],
            top=TOP_K,
        )
        return [doc for doc in search_result]

    elif search_type == "semantic":
        search_result = azure_client.search(
            search_text=user_query, query_type="semantic", semantic_configuration_name="semantic_search", top=TOP_K
        )

        results = [doc for doc in search_result]
        filtered_results = filter_data_by_reranker_score(results, THRESHOLD)
        return filtered_results


class RAGAssistantAgent:
    def __init__(self, thread_id: Union[str, None]):
        # setting up retriever
        client = AzureOpenAI(
            api_key=os.getenv("GPT4_TURBO_AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("GPT4_ASSISTANT_OPENAI_API_VERSION"),
            azure_endpoint=os.getenv("GPT4_TURBO_AZURE_OPENAI_ENDPOINT"),
        )

        assistant_id = os.getenv("RAG_AZURE_ASSISTANT_ID")
        my_assistant = client.beta.assistants.retrieve(assistant_id)
        if thread_id:
            self.thread_id = thread_id
        else:
            empty_thread = client.beta.threads.create()
            self.thread_id = empty_thread.id

        self.agent = OpenAIAssistantRunnable(assistant_id=assistant_id, client=client, as_agent=True)

    def unique_relevant_docs(self, docs):
        unique_file_paths = set()
        filtered_docs = []
        for doc in docs:
            if doc["metadata_spo_item_weburi"] not in unique_file_paths:
                filtered_docs.append(doc)
                unique_file_paths.add(doc["metadata_spo_item_weburi"])
        return filtered_docs

    def execute_agent(self, input: str):
        response = self.agent.invoke(input={"content": input, "thread_id": self.thread_id})
        relevant_docs = []
        while not isinstance(response, AgentFinish):
            tool_outputs = []
            for action in response:
                tool_output, relevant_docs = get_documents(action.tool_input)
                tool_outputs.append({"output": tool_output, "tool_call_id": action.tool_call_id})
            response = self.agent.invoke(
                {
                    "tool_outputs": tool_outputs,
                    "run_id": action.run_id,
                    "thread_id": action.thread_id,
                }
            )
        filtered_relevant_docs = self.unique_relevant_docs(relevant_docs)
        return {
            "output": response.return_values["output"],
            "thread_id": response.return_values["thread_id"],
            "relevant_docs": filtered_relevant_docs,
        }
