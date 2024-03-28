import os 
from typing import List
from uuid import UUID
from langchain.tools import tool

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery

THRESHOLD = 0.3
TOP_K = 5

@tool
def get_documents(prompt: str, knowledge_files_ids: List[UUID]):
    """This tool is for getting relevant documents"""
    print(prompt, "---prompt")
    relevant_docs = get_documents_from_azure_search(
        user_query=prompt,
        search_type="semantic",
        knowledge_files_ids=knowledge_files_ids
    )
    final_docs_content = ""
    for doc in relevant_docs:
        final_docs_content = (
            final_docs_content
            + f"FILE NAME: {doc['fileName']}\nFILE CONTENT: {doc['content']}\n\n"
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
    embedding = client.embeddings.create(
        input=[text], 
        model=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME")
    )
    return embedding.data[0].embedding


def get_documents_from_azure_search(user_query: str, search_type: str, knowledge_files_ids: List[UUID]):
    credential = AzureKeyCredential(os.getenv("AZURE_COGNITIVE_SEARCH_API_KEY"))
    azure_client = SearchClient(
        endpoint=os.getenv("AZURE_COGNITIVE_SEARCH_INDEX_URL"),
        index_name=os.getenv("AZURE_COGNITIVE_SEARCH_ASSISTANTS_INDEX_NAME"),
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
                "metadata_spo_item_weburi"
            ],
            top=TOP_K
        )
        return [doc for doc in search_result]
    
    elif search_type == "semantic":
        search_result = azure_client.search(
            search_text=user_query, 
            query_type="semantic", 
            semantic_configuration_name="semantic_search",
            top=TOP_K
        )

        results = [doc for doc in search_result]
        filtered_results = filter_data_by_reranker_score(results, THRESHOLD)
        return filtered_results