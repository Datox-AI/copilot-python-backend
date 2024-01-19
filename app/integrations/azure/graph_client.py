
from configparser import SectionProxy
from azure.identity import DeviceCodeCredential
from msgraph import GraphServiceClient
from typing import Annotated
import os
from dotenv import load_dotenv
from fastapi import Depends

from app.schemas.identity.current_user import CurrentUser
from app.shared.auth.azure_scheme import current_user

load_dotenv()

AZURE_AD_CLIENT_ID = os.getenv("AZURE_AD_CLIENT_ID")
AZURE_AD_CLIENT_SECRET = os.getenv('AZURE_AD_CLIENT_SECRET')

class Graph:
    device_code_credential: DeviceCodeCredential
    user_client: GraphServiceClient
    
    def __init__(self, user: Annotated[CurrentUser, Depends(current_user)]):
        self.user = user
        
        
        
class Graph:
    

    def __init__(self, config: SectionProxy):
        self.settings = config
        client_id = self.settings['clientId']
        tenant_id = self.settings['tenantId']
        graph_scopes = self.settings['graphUserScopes'].split(' ')

        self.device_code_credential = DeviceCodeCredential(client_id, tenant_id = tenant_id)
        self.user_client = GraphServiceClient(self.device_code_credential, graph_scopes)