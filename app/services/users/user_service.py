from httpx import AsyncClient
from typing import Annotated, List
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from msal import ConfidentialClientApplication
from dotenv import load_dotenv
import os

from app.backend.session import create_admindb_session
from app.models.admindb import ApplicationUser, Role
from app.schemas.identity.current_user import CurrentUser
from app.schemas.users import ApplicationUserMapper
from app.shared.auth.azure_scheme import current_user

load_dotenv()  # Загрузка переменных окружения из .env файла


# Конфигурация для MSAL
TENANT_ID = os.getenv("AZURE_AD_TENANT_ID")
CLIENT_ID = os.getenv("AZURE_AD_CLIENT_ID")
CLIENT_SECRET = "hv38Q~A60Kc0MuphDEojCOX7Dm3iVXTbss0ZkbgR"
AZURE_AD_FRONTEND_CLIENT_ID = os.getenv("AZURE_AD_FRONTEND_CLIENT_ID")
AUTHORITY = os.getenv("AUTHORITY")
# SCOPE = os.getenv("SCOPE")
SCOPE = "https://graph.microsoft.com/.default"


# Создание клиента MSAL
client_app = ConfidentialClientApplication(
    CLIENT_ID,
    authority=AUTHORITY,
    client_credential=CLIENT_SECRET,
)


class ApplicationUserService:
    def __init__(
        self,
        user: Annotated[CurrentUser, Depends(current_user)],
        session: Annotated[Session, Depends(create_admindb_session)],
    ) -> None:
        self.session = session
        self.user = user
        self.graph_client = AsyncClient(base_url='https://graph.microsoft.com/v1.0')

    async def get_access_token(self) -> str:
        # Получение токена для графа Microsoft
        token_response = client_app.acquire_token_for_client(scopes=[SCOPE])
        if not token_response.get("access_token"):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Не удалось получить токен")
        return token_response["access_token"]  # Возвращаем строку токена напрямую

    def get_users(self):
        application_users = self.session.query(ApplicationUser).all()
        return [ApplicationUserMapper.map_to_application_user_response(user) for user in application_users]

    def get_roles(self):
        application_user_roles = self.session.query(Role).all()
        return [ApplicationUserMapper.map_to_application_user_role_response(role) for role in application_user_roles]
    
    async def get_user_roles(self, user_id: str) -> List[str]:
        access_token = await self.get_access_token()
        access_token_2 = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6ImtXYmthYTZxczh3c1RuQndpaU5ZT2hIYm5BdyJ9.eyJhdWQiOiJiZmE4M2VhMy1mNmJmLTRmNDctODI0YS0xNTIyYTUxMjc2Y2EiLCJpc3MiOiJodHRwczovL2xvZ2luLm1pY3Jvc29mdG9ubGluZS5jb20vOTVjMjI4ZjQtOTQ0Yy00OWJhLWFiY2QtYTAwOTg1ZTU0OTdjL3YyLjAiLCJpYXQiOjE3MDg2MDc2MTksIm5iZiI6MTcwODYwNzYxOSwiZXhwIjoxNzA4NjEyMzYxLCJhaW8iOiJBV1FBbS84V0FBQUF4RVhLZTdwR09sNGozZzU5YUduZ2lyeTI0TFZUVXJEZUxQbHVUa1I2Qkpzb3VGanpKUFBhMjU5cWtoZGRRblJqNCtKL2FZR0dMRk5PYVZDUituSU1tM2k2U2gwb3pBdVA3cG1Wa3Q5TzB3SXJMaGhtYkpuRVc2eXFQZlNuZk5QZCIsImF6cCI6IjdmMzA1ZTIxLWRiOGMtNDYyZC05OTRkLTFmYWUzMTViOWJmMCIsImF6cGFjciI6IjAiLCJuYW1lIjoiSWxraG9tIEtoYWZpem92Iiwib2lkIjoiNWY2MmQ2MjEtY2JiNi00NWNlLWExYTUtNmQzNTMyMDdhZmI4IiwicHJlZmVycmVkX3VzZXJuYW1lIjoiaWxraG9tQGRhdG94LmFpIiwicmgiOiIwLkFVWUE5Q2pDbFV5VXVrbXJ6YUFKaGVWSmZLTS1xTC1fOWtkUGdrb1ZJcVVTZHNxQUFEWS4iLCJyb2xlcyI6WyJBZG1pbiIsIlVzZXIiXSwic2NwIjoidXNlcl9pbXBlcnNvbmF0aW9uIiwic3ViIjoic0Z2dG1uckM2NGFpeUwzRU5GOEdnRHR6U3JObC00Z2JBUUY1TWRBdkpycyIsInRpZCI6Ijk1YzIyOGY0LTk0NGMtNDliYS1hYmNkLWEwMDk4NWU1NDk3YyIsInV0aSI6ImVRV3VTUnM0bzBPYkU3SUNsSW9DQUEiLCJ2ZXIiOiIyLjAifQ.Xj4kIsh--mb_jX9SO7p1cqGWufLYiDAw3_tVsCkDConx89K3Wb0nXlHvNNGaJKbUP9kWI-onoeaZIIH5Xs3n59de1IXz0XSWQNp_c4q8HBACtc559lMgaxqWb2_kpy9PjoNv1sFqMB_aJggp04NODfH1ZF5ic94R0oWR7sNSOBYoxmXOZHOx9TS9IPR2zrvvRh7holvsWCR7UkYOmS6C_7H_onpcw4tCr1m-pUm3fWDcQlM7l-0stTrLJsOvbvnSLIyseQ3vFw83nCE6VzR73DsK1wcaxrwLU7OVtQ-ZV69GP36xawgVy3KJ9SxXgn-QbUqsjKnZgoAs8nBmbhLPXQ"
        print(access_token)
        print(access_token_2)
        self.graph_client.headers = {'Authorization': f'Bearer {access_token}'}
        response = await self.graph_client.get(f'/users/{user_id}/appRoleAssignments')
        response.raise_for_status()
        roles = response.json().get('value', [])
        return [role['appRoleId'] for role in roles]

    async def update_user_roles(self, user_id: str, new_role_ids: List[str]):
        current_role_ids = await self.get_user_roles(user_id)
        roles_to_add = set(new_role_ids) - set(current_role_ids)
        roles_to_remove = set(current_role_ids) - set(new_role_ids)

        for role_id in roles_to_add:
            await self.add_role_to_user(user_id, role_id)

        for role_id in roles_to_remove:
            assignment_id = await self.get_role_assignment_id(user_id, role_id)
            if assignment_id:
                await self.remove_role_from_user(user_id, assignment_id)

    async def add_role_to_user(self, user_id: str, role_id: str, resource_id: str):
        app_role_assignment = {
            "principalId": user_id,
            "resourceId": resource_id,  # ID ресурса (обычно ID приложения в Azure AD)
            "appRoleId": role_id  # ID роли, которую вы хотите назначить
        }
        access_token = await self.get_access_token()
        self.graph_client.headers.update({'Authorization': f'Bearer {access_token}'})
        response = await self.graph_client.post(f'/users/{user_id}/appRoleAssignments', json=app_role_assignment)
        if response.status_code != 201:
            raise HTTPException(status_code=response.status_code, detail="Failed to add role to user")

    async def remove_role_from_user(self, user_id: str, role_assignment_id: str):
        access_token = await self.get_access_token()
        self.graph_client.headers.update({'Authorization': f'Bearer {access_token}'})
        response = await self.graph_client.delete(f'/users/{user_id}/appRoleAssignments/{role_assignment_id}')
        if response.status_code != 204:
            raise HTTPException(status_code=response.status_code, detail="Failed to remove role from user")

    async def get_role_assignment_id(self, user_id: str, role_id: str) -> str:
        access_token = await self.get_access_token()
        self.graph_client.headers.update({'Authorization': f'Bearer {access_token}'})
        response = await self.graph_client.get(f'/users/{user_id}/appRoleAssignments')
        if response.status_code == 200:
            assignments = response.json().get('value', [])
            for assignment in assignments:
                if assignment['appRoleId'] == role_id:
                    return assignment['id']
        return None
