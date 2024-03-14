import os
import uuid
from typing import Annotated

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SimpleField,
    VectorSearch,
    VectorSearchProfile,
)
from azure.search.documents.models import VectorFilterMode, VectorizedQuery
from langchain.tools import tool
from dotenv import load_dotenv
from openai import AzureOpenAI
from app.schemas.identity.current_user import CurrentUser
from app.shared.auth.azure_scheme import current_user
from app.backend.session import create_maindb_session
from fastapi import Depends
from sqlalchemy.orm import Session
from .text_processor import TextProcessor
from .user_files_services import UserFileService
import shutil
import tempfile
from pathlib import Path

from fastapi import Depends, UploadFile



class AzureSearchIndexManager:
    def __init__(
        self,
        chat_id: uuid.UUID,
        session: Annotated[Session, Depends(create_maindb_session)],
        user: Annotated[CurrentUser, Depends(current_user)]
    ):
        # Load environment variables from a .env file if present
        load_dotenv()
        self.chat_id = chat_id
        self.user = user
        self.session = session
        # Initialize Azure OpenAI client
        self.openai_client = AzureOpenAI(
            azure_endpoint=os.environ.get("GPT4_TURBO_AZURE_OPENAI_ENDPOINT"),
            api_key=os.environ.get("GPT4_TURBO_AZURE_OPENAI_API_KEY"),
            api_version=os.environ.get("GPT4_TURBO_OPENAI_API_VERSION")
        )

        # Setup Azure Search Index Client
        self.credential = AzureKeyCredential(os.environ.get("AZURE_COGNITIVE_SEARCH_API_KEY"))
        self.index_client = SearchIndexClient(
            endpoint=os.environ.get("AZURE_COGNITIVE_SEARCH_INDEX_URL"), credential=self.credential
        )
        self.text_processor = TextProcessor()

        self.index_name = "test-index-1"
        self.search_client = SearchClient(os.environ.get("AZURE_COGNITIVE_SEARCH_INDEX_URL"),
                                          index_name=self.index_name,
                                          credential=self.credential)
        
        self.user_file_service = UserFileService(session=session, user=user)

    def create_search_index(self):
        fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True, sortable=True, filterable=True,
                        facetable=True),
            SearchableField(name="content", type=SearchFieldDataType.String, filterable=True),
            SearchableField(name="file_type", type=SearchFieldDataType.String, filterable=True),
            SearchableField(name="userId", type=SearchFieldDataType.String, filterable=True),
            SearchableField(name="chatId", type=SearchFieldDataType.String, filterable=True),
            SearchableField(name="fileId", type=SearchFieldDataType.String, filterable=True),
            SearchField(name="contentVector", type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                        searchable=True, vector_search_dimensions=1536, vector_search_profile_name="myHnswProfile")
        ]

        vector_search = VectorSearch(
            algorithms=[
                HnswAlgorithmConfiguration(name="hello1", kind="hnsw",
                                           parameters={"m": 4,
                                                       "efConstruction": 400,
                                                       "efSearch": 500,
                                                       "metric": "cosine"
                                                       })
            ],
            profiles=[
                VectorSearchProfile(name="myHnswProfile", algorithm_configuration_name="hello1")
            ]
        )

        index = SearchIndex(name=self.index_name, fields=fields, vector_search=vector_search)
        result = self.index_client.create_or_update_index(index)
        print(f'Index {result.name} created')

    def generate_embeddings(self, text):
        response = self.openai_client.embeddings.create(input=text, model=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME"))
        return response.data[0].embedding

    def add_or_update_documents(self, documents):
        self.search_client.merge_or_upload_documents(documents=documents)

    def save_temp_file(self, upload_file: UploadFile):
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(upload_file.filename).suffix) as temp_file:
                shutil.copyfileobj(upload_file.file, temp_file)
                temp_file_path = temp_file.name
                file_extension = upload_file.content_type  # Используем MIME тип как "расширение"
        finally:
            upload_file.file.close()
        return temp_file_path, file_extension

    def process_and_store_texts(self, pdf_data, file_id):
        # pdf_data = self.user_file_service.download_file(file_id=file_id)
        # pdf_data_path = self.save_temp_file(upload_file=pdf_data)[0]
        # pdf_file_content = open(pdf_data_path, "rb")
        extracted_texts = self.text_processor.extract_texts(pdf_data)
        chunked_texts = self.text_processor.chunk_texts(extracted_texts)

        file_id = str(file_id)
        chat_id = str(self.chat_id)
        user_id = str(self.user.user_id)
        print(file_id, " file_id")
        print(chat_id, " chat_id")
        print(user_id, " user_id")
        
        chunk_documents = []
        for chunk_text in chunked_texts:
            chunk_embeddings = self.generate_embeddings(chunk_text)
            chunk_document = {
                "id": str(uuid.uuid4()),
                "file_type": "application/pdf",
                "userId": user_id,
                "chatId": chat_id,
                "fileId": file_id,
                "content": chunk_text,
                "contentVector": chunk_embeddings
            }
            chunk_documents.append(chunk_document)
        print(len(chunk_documents), " --- chunks")
        # Call add_or_update_documents only once after processing all chunks
        self.add_or_update_documents(chunk_documents)

    def search_documents(self, prompt, chat_id, file_id):
        embedding = self.generate_embeddings(prompt)
        vector_query = VectorizedQuery(vector=embedding, k_nearest_neighbors=3,
                                       fields="contentVector")
        if file_id:
            filter = f"chatId eq '{chat_id}' and fileId eq '{file_id}'"
        else:
            filter = f"chatId eq '{chat_id}'"

        results = self.search_client.search(
            search_text=None,
            vector_queries=[vector_query],
            vector_filter_mode=VectorFilterMode.PRE_FILTER,
            filter=filter,
            select=["content", "fileId", "chatId"],
        )
        text_content = ""
        for result in results:
            text_content += f"{result['content']}"
        print(text_content)
        return text_content

    def invoke(self, file_data, file_id, prompt):
        chunk_documents = self.process_and_store_texts(pdf_data=file_data, file_id=file_id)