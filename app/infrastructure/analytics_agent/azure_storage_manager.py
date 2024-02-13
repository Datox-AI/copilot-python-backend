import os
import uuid

import pandas as pd
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceNotFoundError
from dotenv import load_dotenv
from fastapi import UploadFile, HTTPException

load_dotenv()


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

    def delete_extra_files(self, message_id: str, stored_file_id: str):
        file_full_name = f"{message_id}_{stored_file_id}.csv"
        blob_list = self.container_client.list_blobs(name_starts_with=file_full_name)
        for blob in blob_list:
            if blob.name != file_full_name:
                self.container_client.delete_blob(blob=blob)

    def download_csv_file(self, stored_file_id: str):    
        try:
            downloaded_stream_file = self.container_client.download_blob(blob=stored_file_id)
        except ResourceNotFoundError:
            raise HTTPException(status_code=404, detail=f"File (name: {stored_file_id}) not found")
        return downloaded_stream_file

    def upload_file(self, file: UploadFile) -> str:
        file_id = str(uuid.uuid4())
        blob_client = self.container_client.get_blob_client(blob=file_id)
        metadata = {"media_type": file.content_type}
        blob_client.upload_blob(file.file, metadata=metadata)
        return file_id

    def download_pdf_file(self, file_id: uuid.UUID):
        blob_client = self.container_client.get_blob_client(blob=str(file_id))
        properties = blob_client.get_blob_properties()
        media_type = properties.metadata.get("media_type", "application/pdf")

        stream = blob_client.download_blob().readall()

        return stream, media_type
    
