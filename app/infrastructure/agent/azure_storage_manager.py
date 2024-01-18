import os 
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient
import pandas as pd
import uuid

load_dotenv()


class AzureBlobStorageManager:
    
    def __init__(self):
        # initiating blob service client
        az_storage_connection_string = os.environ["AZURE_STORAGE_CONNECTION_STRING"]
        az_storage_agent_container_name = os.environ["AZURE_STORAGE_DA_AGENT_CONTAINER"]
        blob_service_client = BlobServiceClient.from_connection_string(az_storage_connection_string)
        
        self.container_client = blob_service_client.get_container_client(
            container=az_storage_agent_container_name
        )
    
    def upload_csv(self, df: pd.DataFrame, message_id: str):
        store_id = uuid.uuid4().hex
        file_full_name = f"{message_id}_{store_id}.csv"
        #uploading 
        self.container_client.upload_blob(name=file_full_name, data=df.to_csv(index=False), overwrite=True)     
        
        return store_id
    

    def delete_extra_files(self, message_id: str, store_id: str):
        file_full_name = f"{message_id}_{store_id}.csv"
        blob_list = self.container_client.list_blobs(name_starts_with=file_full_name)
        for blob in blob_list:
            if blob.name != file_full_name:
                self.container_client.delete_blob(blob=blob)
