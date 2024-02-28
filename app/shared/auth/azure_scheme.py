import os
from typing import Annotated

from dotenv import load_dotenv
from fastapi import Depends
from fastapi_azure_auth import MultiTenantAzureAuthorizationCodeBearer
from fastapi_azure_auth.exceptions import InvalidAuth
from fastapi_azure_auth.user import User

from app.schemas.identity import CurrentUser, CurrentUserRequest
from app.services.identity import CheckUpdateUser

from ..context import current_user_id

load_dotenv(override=True)

AZURE_AD_CLIENT_ID = os.getenv("AZURE_AD_CLIENT_ID")
AZURE_AD_FRONTEND_CLIENT_ID = os.getenv("AZURE_AD_FRONTEND_CLIENT_ID")


azure_scheme = MultiTenantAzureAuthorizationCodeBearer(
    app_client_id=AZURE_AD_CLIENT_ID,
    scopes={
        f"api://{AZURE_AD_CLIENT_ID}/user_impersonation": "user_impersonation",
    },
    validate_iss=False,
)


async def multi_auth(
    azure_auth: Annotated[User, Depends(azure_scheme)],
    checkUpdateUser: Annotated[CheckUpdateUser, Depends()],
) -> CurrentUser:
    if not azure_auth:
        raise InvalidAuth("You must either provide a valid bearer token or API key")
    #

    azure_object_id = azure_auth.claims.get("oid")
    tenant_id = azure_auth.claims.get("tid")
    user_name = azure_auth.claims.get("name")
    roles = azure_auth.claims.get("roles", [])
    print(roles, " roles from token --------")

    currentUserRequest = CurrentUserRequest(
        azure_object_id=azure_object_id,
        tenant_id=tenant_id,
        name=user_name,
        roles=roles,
    )
    current_user = await checkUpdateUser.invoke(currentUserRequest)
    current_user_id.set(current_user.user_id)
    return current_user


def current_user(current_user: Annotated[CurrentUser, Depends(multi_auth)]) -> CurrentUser:
    return current_user
