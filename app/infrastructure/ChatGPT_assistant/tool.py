from openai import AzureOpenAI
import os 
from dotenv import load_dotenv
from langchain.tools import tool
from azure.search.documents.models import VectorFilterMode, VectorizedQuery
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential



load_dotenv()

openai_client = AzureOpenAI(
    azure_endpoint=os.environ.get("GPT4_TURBO_AZURE_OPENAI_ENDPOINT"),
    api_key=os.environ.get("GPT4_TURBO_AZURE_OPENAI_API_KEY"),
    api_version=os.environ.get("GPT4_TURBO_OPENAI_API_VERSION")
)

search_client = SearchClient(
    endpoint=os.environ.get("AZURE_COGNITIVE_SEARCH_INDEX_URL"),
    index_name=os.environ.get("AZURE_COGNITIVE_SEARCH_CHATGPT_INDEX_NAME"),
    credential=AzureKeyCredential(os.environ.get("AZURE_COGNITIVE_SEARCH_API_KEY"))
)

@tool
def search_documents(query, user_id, chat_id, file_id):
    response = openai_client.embeddings.create(
        input=query, 
        model=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME")
    )
    embedding = response.data[0].embedding
    vector_query = VectorizedQuery(
        vector=embedding, k_nearest_neighbors=3, fields="contentVector"
    )
    if file_id:
        filter = f"userId eq {user_id} and chatId eq '{chat_id}' and fileId eq '{file_id}'",
    else:
        filter = f"userId eq {user_id} and chatId eq '{chat_id}'"

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
        
    return text_content
     