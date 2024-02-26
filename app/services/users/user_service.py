import os
from typing import List
from uuid import UUID
from httpx import AsyncClient
from fastapi import HTTPException, Depends, status
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session
from msal import ConfidentialClientApplication
from dotenv import load_dotenv

from app.backend.session import create_admindb_session
from app.models.admindb import ApplicationUser, Role, UserRole
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
        service_principal = service_principals.get("value", [])
        if service_principal:
            return service_principal[0]["id"]
        else:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service Principal not found")

    async def get_user_role(self, user_id: UUID, resource_id: UUID) -> str:
        current_roles_response = await self.client.get(
            f"users/{user_id}/appRoleAssignments", params={"$select": "id,principalId,resourceId,appRoleId"}
        )
        if current_roles_response.status_code != 200:
            raise HTTPException(status_code=current_roles_response.status_code, detail="Failed to fetch current roles")

        current_roles = current_roles_response.json().get("value", [])
        current_role_ids = [role["appRoleId"] for role in current_roles if role["resourceId"] == resource_id]
        return str(list(set(current_role_ids))[0])

    async def update_user_roles(self, user_id: UUID, resource_id: UUID, new_role_ids: List[UUID]) -> None:
        # Fetch the current roles assigned to the user for the specified resource
        current_roles_response = await self.client.get(
            f"users/{user_id}/appRoleAssignments", params={"$select": "id,principalId,resourceId,appRoleId"}
        )
        if current_roles_response.status_code != 200:
            raise HTTPException(status_code=current_roles_response.status_code, detail="Failed to fetch current roles")

        current_roles = current_roles_response.json().get("value", [])
        current_role_ids = set([role["appRoleId"] for role in current_roles if role["resourceId"] == resource_id])

        new_role_ids_set = {str(item) for item in new_role_ids}
        role_ids_to_add = list(new_role_ids_set - current_role_ids)
        role_ids_to_remove = list(current_role_ids - new_role_ids_set)

        for role_id in role_ids_to_add:
            app_role_assignment = {
                "principalId": str(user_id),
                "resourceId": str(resource_id),
                "appRoleId": str(role_id),
            }
            add_response = await self.client.post(f"users/{str(user_id)}/appRoleAssignments", json=app_role_assignment)
            if add_response.status_code != 201:
                try:
                    error_details = add_response.json()
                except ValueError:
                    raise HTTPException(
                        status_code=add_response.status_code, detail="Failed to add role due to an unexpected error"
                    )
                if (
                    add_response.status_code == 400 and "error" in error_details and "Permission being assigned already exists on the object"
                    in error_details["error"].get("message", "")
                ):
                    return "Role is already assigned to user."
                else:
                    raise HTTPException(
                        status_code=add_response.status_code,
                        detail=error_details.get("error", {}).get(
                            "message", "Failed to add role due to an unexpected error"
                        ),
                    )

        for role_id in role_ids_to_remove:
            role_assignment_id = next(
                (role["id"] for role in current_roles if role["appRoleId"] == role_id and role["resourceId"] == resource_id), None
            )
            if role_assignment_id:
                response = await self.client.delete(f"users/{str(user_id)}/appRoleAssignments/{role_assignment_id}")
                response.raise_for_status()
            else:
                print(f"No role assignment found for role ID {role_id} to remove")


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
                    role_definitions.append({"azure_role_id": role_id, "name": role_display_name})
        await self.__sync_roles_with_db(self.session, role_definitions)
        return role_definitions

    def get_users(self) -> List[dict]:
        application_users = self.session.query(ApplicationUser).all()
        return [ApplicationUserMapper.map_to_application_user_response(user) for user in application_users]

    async def get_user_role(self, user_id: UUID) -> str:
        access_token = await self.token_provider.get_access_token()
        graph_client = GraphApiClient(access_token)
        service_principals_id = await graph_client.get_service_principal_id(os.getenv("AZURE_AD_CLIENT_ID"))
        return await graph_client.get_user_role(user_id, service_principals_id)

    async def update_user_roles_for_user(self, user_id: UUID, new_role_ids: List[UUID]) -> None:
        access_token = await self.token_provider.get_access_token()
        graph_client = GraphApiClient(access_token)
        service_principals_id = await graph_client.get_service_principal_id(os.getenv("AZURE_AD_CLIENT_ID"))
        response = await graph_client.update_user_roles(user_id, service_principals_id, new_role_ids)
        if response:
            await self.__sync_user_roles_with_db(self.session, user_id, new_role_ids)
        return response

    async def __sync_roles_with_db(self, session: Session, roles_data: List[dict]):
        for role_data in roles_data:
            azure_role_id = role_data["azure_role_id"]
            role_name = role_data["name"]
            role = session.query(Role).filter_by(name=role_name).first()

            if role:
                if role.azure_role_id != azure_role_id:
                    role.azure_role_id = azure_role_id
            else:
                role = Role(name=role_name, azure_role_id=azure_role_id)
                session.add(role)

        session.commit()

    async def __sync_user_roles_with_db(self, session: Session, user_azure_object_id: UUID, new_role_ids: List[UUID]):
        user = (
            session.query(ApplicationUser).filter(ApplicationUser.azure_object_id == str(user_azure_object_id)).first()
        )
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        current_roles = {user_role.role.azure_role_id for user_role in user.user_roles}

        new_role_ids_set = {str(role_id) for role_id in new_role_ids}

        roles_to_add = new_role_ids_set - current_roles
        roles_to_remove = current_roles - new_role_ids_set

        for role_id in roles_to_remove:
            role_obj = session.query(Role).filter_by(azure_role_id=role_id).first()
            user_roles_to_remove = session.query(UserRole).filter_by(role_id=role_obj.id).filter_by(user_id=user.id).all()
            for user_role in user_roles_to_remove:
                session.delete(user_role)
                session.commit()

        for role_id in roles_to_add:
            role = session.query(Role).filter(Role.azure_role_id == role_id).first()
            if not role:
                role = Role(azure_role_id=role_id, name="Unknown Role")
                session.add(role)
                session.flush()

            user_role = UserRole(user_id=user.id, role_id=role.id, azure_role_id=role_id)
            session.add(user_role)

        session.commit()
