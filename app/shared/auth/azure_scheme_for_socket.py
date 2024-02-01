from fastapi import Depends
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTClaimsError, JWTError
from typing import Any, Annotated
from app.enums import AzureTokenErrorMessagesEnum
from dotenv import load_dotenv
from app.services.identity import CheckUpdateUser
from app.schemas.identity import CurrentUser, CurrentUserRequest
import pprint
import os, asyncio
from fastapi_azure_auth.openid_config import OpenIdConfig
from fastapi_azure_auth.user import User
from fastapi_azure_auth.utils import is_guest


load_dotenv(override=True)
AZURE_AD_CLIENT_ID = os.getenv("AZURE_AD_CLIENT_ID")
validate_iss = False


async def validate_azure_token(
    access_token: str,
    check_update_user: Annotated[CheckUpdateUser, Depends()],
):
    user = False
    error_message = AzureTokenErrorMessagesEnum.default.value
    try:
        # Extract header information of the token.
        header: dict[str, str] = jwt.get_unverified_header(token=access_token) or {}
        claims: dict[str, Any] = jwt.get_unverified_claims(token=access_token) or {}
    except:
        error_message = AzureTokenErrorMessagesEnum.invalid_token.value
        return user, error_message
    # checking if user is guest
    user_is_guest = is_guest(claims=claims)
    if user_is_guest:
        error_message = AzureTokenErrorMessagesEnum.guest_user.value
        return user, error_message
    # creating openidConfig
    openid_config = OpenIdConfig(
        multi_tenant=True,
        token_version=2,
        app_id=AZURE_AD_CLIENT_ID,
    )
    await openid_config.load_config()
    iss = openid_config.issuer

    try:
        if key := openid_config.signing_keys.get(header.get("kid", "")):
            # We require and validate all fields in an Azure AD token
            options = {
                "verify_signature": True,
                "verify_aud": True,
                "verify_iat": True,
                "verify_exp": True,
                "verify_nbf": True,
                "verify_iss": validate_iss,
                "verify_sub": True,
                "verify_jti": True,
                "verify_at_hash": True,
                "require_aud": True,
                "require_iat": True,
                "require_exp": True,
                "require_nbf": True,
                "require_iss": validate_iss,
                "require_sub": True,
                "require_jti": False,
                "require_at_hash": False,
                "leeway": 0,
            }
            # Validate token
            token = jwt.decode(
                access_token,
                key=key,
                algorithms=["RS256"],
                audience=AZURE_AD_CLIENT_ID,
                issuer=iss,
                options=options,
            )
            # Attach the user to the request. Might not be necessary, just copying and paste from fastapi_azure_auth library
            azure_auth = User(
                **{
                    **token,
                    "claims": token,
                    "access_token": access_token,
                    "is_guest": user_is_guest,
                }
            )
            #
            azure_object_id = azure_auth.claims.get("oid")
            tenant_id = azure_auth.claims.get("tid")
            user_name = azure_auth.claims.get("name")
            roles = azure_auth.claims.get("roles", [])
            currentUserRequest = CurrentUserRequest(
                azure_object_id=azure_object_id,
                tenant_id=tenant_id,
                name=user_name,
                roles=roles,
            )
            user = await check_update_user.invoke(currentUserRequest)

    except JWTClaimsError as error:
        error_message = AzureTokenErrorMessagesEnum.invalid_claims.value
    except ExpiredSignatureError as error:
        error_message = AzureTokenErrorMessagesEnum.signature_expired.value
    except JWTError as error:
        error_message = AzureTokenErrorMessagesEnum.unable_to_validate.value
    except Exception as error:
        # Extra failsafe in case of a bug in a future version of the jwt library
        error_message = AzureTokenErrorMessagesEnum.unknown_error.value
    finally:
        return user, error_message
