import os
import uuid
import pandas as pd
from datetime import datetime

from azure.core.exceptions import ResourceNotFoundError
from azure.storage.blob import BlobServiceClient
from azure.storage.blob.aio import BlobServiceClient as AsyncBlobServiceClient
from dotenv import load_dotenv
from fastapi import HTTPException, UploadFile
from app.models.maindb.file import File
from app.models.maindb.assistants import AssistantFile, Assistant
from sqlalchemy.orm import Session
from typing import List
from tempfile import NamedTemporaryFile
import aiofiles

load_dotenv(override=True)


class AzureBlobStorageManager:
    def __init__(self, container_name):
        # initiating blob service client
        az_storage_connection_string = os.environ["AZURE_STORAGE_CONNECTION_STRING"]
        blob_service_client = BlobServiceClient.from_connection_string(az_storage_connection_string)

        self.container_client = blob_service_client.get_container_client(container=container_name)

    def upload_csv(self, df: pd.DataFrame, message_id: str):
        stored_file_id = uuid.uuid4().hex
        file_full_name = f"{message_id}_{stored_file_id}.csv"
        # uploading
        self.container_client.upload_blob(name=file_full_name, data=df.to_csv(index=False), overwrite=True)

        return stored_file_id

    def delete_extra_csv_files(self, message_id: str, stored_file_id: str):
        file_full_name = f"{message_id}_{stored_file_id}.csv"
        blob_list = self.container_client.list_blobs(name_starts_with=file_full_name)
        for blob in blob_list:
            if blob.name != file_full_name:
                self.container_client.delete_blob(blob=blob)

    def download_csv_file(self, stored_file_id: str):
        try:
            blob_client = self.container_client.get_blob_client(blob=str(stored_file_id))
            properties = blob_client.get_blob_properties()
            media_type = "text/csv"
            downloaded_stream_file = blob_client.download_blob()
            return downloaded_stream_file, media_type

        except ResourceNotFoundError:
            raise HTTPException(status_code=404, detail=f"File (name: {stored_file_id}) not found")

    def upload_file(self, file: UploadFile) -> str:
        file_id = str(uuid.uuid4())
        blob_client = self.container_client.get_blob_client(blob=file_id)
        file_content_type = file.content_type
        print(file_content_type, " content")
        metadata = {"media_type": file.content_type}
        blob_client.upload_blob(file.file, metadata=metadata)
        return file_id

    def blob_upload_file(self, file: UploadFile, metadata=None) -> str:
        file_id = str(uuid.uuid4())
        blob_client = self.container_client.get_blob_client(blob=file_id)
        if not metadata:
            metadata = {"media_type": file.content_type}
        blob_client.upload_blob(file, metadata=metadata)
        return file_id

    def download_pdf_file(self, file_id: uuid.UUID):
        blob_client = self.container_client.get_blob_client(blob=str(file_id))
        properties = blob_client.get_blob_properties()
        media_type = properties.metadata.get("media_type", "application/pdf")

        stream = blob_client.download_blob().readall()

        return stream, media_type


class AzureAsyncBlobStorageManager:
    def __init__(self, container_name):
        # initiating blob service client
        az_storage_connection_string = os.environ["AZURE_STORAGE_CONNECTION_STRING"]
        self.blob_service_client = AsyncBlobServiceClient.from_connection_string(az_storage_connection_string)

        self.container_client = self.blob_service_client.get_container_client(container=container_name)

    async def close(self):
        await self.blob_service_client.close()

    async def save_and_upload_file(self, session: Session, file: UploadFile, file_id: str):
        file_name = file.filename
        file_extension = file_name.split(".")[-1]
        blob_name = f"{file_id}.{file_extension}"
        try:
            metadata = {"media_type": file.content_type}
            blob_client = self.container_client.get_blob_client(blob=file_id)
            data = await file.read()
            await blob_client.upload_blob(data=data, metadata=metadata, overwrite=True)
        except Exception as e:
            raise ValueError(f"Ошибка при загрузке файла: {e}")

        new_file = File(id=file_id, file_name=file_name, blob_name=blob_name, file_extension=file_extension)
        session.add(new_file)
        session.commit()

        return file_id

    async def save_and_upload_assistant_file(
        self, file_id: str, file_content: bytes, session: Session, uploaded_file: UploadFile, assistant_obj: Assistant
    ):
        file_name = uploaded_file.filename
        if "." not in file_name:
            raise ValueError("Uploaded file has no extension")
        file_extension = file_name.split(".")[-1]
        blob_name = f"{file_id}.{file_extension}"
        print(blob_name, " blob_name")
        # try:
        metadata = {"media_type": uploaded_file.content_type}
        blob_client = self.container_client.get_blob_client(blob=file_id)
        await blob_client.upload_blob(data=file_content, metadata=metadata, overwrite=True)
        # except Exception as e:
        # raise ValueError(f"Error during file upload: {e}")

        knowledge_file_obj = AssistantFile(
            id=file_id,
            created_at=datetime.now(),
            name=uploaded_file.filename,
            type=uploaded_file.content_type.split("/")[0] if uploaded_file.content_type else None,
            blob_name=blob_name,
            is_deleted=False,
            assistant_id=assistant_obj.assistant_id,
            assistant=assistant_obj,
        )
        session.add(knowledge_file_obj)
        session.commit()

        return file_id

    async def upload_file(self, file: UploadFile) -> str:
        file_id = str(uuid.uuid4())
        blob_client = self.container_client.get_blob_client(blob=file_id)
        file_content_type = file.content_type
        print(file_content_type, " content")
        metadata = {"media_type": file.content_type}
        await blob_client.upload_blob(file.file, metadata=metadata)
        return file_id

    async def download_file(self, file_id: uuid.UUID):
        try:
            blob_client = self.container_client.get_blob_client(blob=str(file_id))
            properties = await blob_client.get_blob_properties()
            media_type = properties.metadata.get("media_type", None)
            downloaded_blob = await blob_client.download_blob()
            stream = await downloaded_blob.readall()
            return stream, media_type
        except ResourceNotFoundError:
            raise HTTPException(status_code=404, detail=f"File (name: {file_id}) not found")
