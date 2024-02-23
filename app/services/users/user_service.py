import os
from typing import List
from httpx import AsyncClient
from fastapi import HTTPException, Depends, status
from sqlalchemy.orm import Session
from msal import ConfidentialClientApplication
from dotenv import load_dotenv

from app.backend.session import create_admindb_session
from app.models.admindb import ApplicationUser
from app.schemas.identity.current_user import CurrentUser
from app.schemas.users import ApplicationUserMapper
from app.shared.auth.azure_scheme import current_user

load_dotenv()


class GraphApiClient:
    def __init__(self, token: str):
        # Initialize the client with the Microsoft Graph API base URL and the authorization token
        self.client = AsyncClient(base_url="https://graph.microsoft.com/v1.0")
        self.client.headers = {"Authorization": f"Bearer {token}"}

    async def get_service_principal(self, client_id: str) -> dict:
        # Fetch the service principal details by client ID
        response = await self.client.get(f"/servicePrincipals?$filter=appId eq '{client_id}'&$select=id,appRoles")
        response.raise_for_status()
        return response.json()

    async def get_service_principal_id(self, client_id: str) -> str:
        # Extract the service principal ID from the response
        service_principals = await self.get_service_principal(client_id)
        if service_principals:
            return service_principals[0]["id"]
        else:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service Principal not found")

    async def update_user_roles(self, user_id: str, resource_id: str, new_role_ids: List[str]) -> None:
        # Fetch the current roles assigned to the user for the specified resource
        current_roles_response = await self.client.get(
            f"users/{user_id}/appRoleAssignments", params={"$select": "id,principalId,resourceId,appRoleId"}
        )
        if current_roles_response.status_code != 200:
            raise HTTPException(status_code=current_roles_response.status_code, detail="Failed to fetch current roles")

        current_roles = current_roles_response.json().get("value", [])
        current_role_ids = [role["appRoleId"] for role in current_roles if role["resourceId"] == resource_id]

        # Compute the roles to add and to remove
        role_ids_to_add = list(set(new_role_ids) - set(current_role_ids))
        role_ids_to_remove = [
            role for role in current_roles if role["appRoleId"] in (set(current_role_ids) - set(new_role_ids))
        ]

        # Compute the roles to add and to remove
        for role_id in role_ids_to_add:
            app_role_assignment = {"principalId": user_id, "resourceId": resource_id, "appRoleId": role_id}
            add_response = await self.client.post(f"users/{user_id}/appRoleAssignments", json=app_role_assignment)
            if add_response.status_code != 201:
                raise HTTPException(status_code=add_response.status_code, detail="Failed to add role")

        # Remove old roles
        for role in role_ids_to_remove:
            delete_response = await self.client.delete(
                f'users/{user_id}/appRoleAssignments/{role["id"]}',
            )
            if delete_response.status_code != 204:
                raise HTTPException(status_code=delete_response.status_code, detail="Failed to remove role")


class TokenProvider:
    def __init__(self, client_id: str, client_secret: str, authority: str, scope: str):
        self.client_app = ConfidentialClientApplication(
            client_id, authority=authority, client_credential=client_secret
        )
        self.scope = scope

    async def get_access_token(self) -> str:
        token_response = self.client_app.acquire_token_for_client(scopes=[self.scope])
        if not token_response.get("access_token"):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Failed to obtain access token")
        return token_response["access_token"]


class ApplicationUserService:
    def __init__(self, user: CurrentUser = Depends(current_user), session: Session = Depends(create_admindb_session)):
        self.session = session
        self.user = user
        self.token_provider = TokenProvider(
            client_id=os.getenv("AZURE_AD_CLIENT_ID"),
            client_secret=os.getenv("AZURE_AD_CLIENT_SECRET"),
            authority="https://login.microsoftonline.com/" + os.getenv("AZURE_AD_TENANT_ID"),
            scope="https://graph.microsoft.com/.default",
        )

    async def get_user_roles(self) -> dict:
        access_token = await self.token_provider.get_access_token()
        graph_client = GraphApiClient(access_token)
        service_principals = await graph_client.get_service_principal(os.getenv("AZURE_AD_CLIENT_ID"))
        role_definitions = []
        service_principal = service_principals.get("value", [])
        if service_principal:
            app_roles = service_principal[0].get("appRoles", [])
            for role in app_roles:
                role_id = role.get("id")
                role_display_name = role.get("displayName")
                if role_id and role_display_name:
                    role_definitions.append({"id": role_id, "name": role_display_name})
        return role_definitions

    def get_users(self) -> List[dict]:
        application_users = self.session.query(ApplicationUser).all()
        return [ApplicationUserMapper.map_to_application_user_response(user) for user in application_users]

    async def update_user_roles_for_user(self, user_id: str, new_role_ids: List[str]) -> None:
        access_token = await self.token_provider.get_access_token()
        graph_client = GraphApiClient(access_token)
        service_principals_id = await graph_client.get_service_principal(os.getenv("AZURE_AD_CLIENT_ID"))
        await graph_client.update_user_roles(user_id, service_principals_id, new_role_ids)
