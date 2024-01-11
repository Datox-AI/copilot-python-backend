from fastapi import (
    Depends,
    FastAPI, 
    Security,
    Cookie,
    Depends,
    FastAPI,
    Query,
    WebSocket,
    WebSocketException,
    status
)
from fastapi.responses import HTMLResponse
from typing import Annotated

from dotenv import load_dotenv
import os
from fastapi_azure_auth.auth import MultiTenantAzureAuthorizationCodeBearer

from .const import (
    OPEN_API_DESCRIPTION,
    OPEN_API_TITLE,
)

from .version import __version__
from app.models.base_models import setup_audit_listeners
from app.routers import (
    chats, agent
)
from .openapi import custom_openapi


load_dotenv() 

AZURE_AD_INSTANCE = os.getenv("AZURE_AD_INSTANCE")
AZURE_AD_TENANT_ID = os.getenv("AZURE_AD_TENANT_ID")
AZURE_AD_AUDIENCE = os.getenv("AZURE_AD_AUDIENCE")
AZURE_AD_FRONTEND_CLIENT_ID = os.getenv('AZURE_AD_FRONTEND_CLIENT_ID')

app = FastAPI(
    title=OPEN_API_TITLE,
    description=OPEN_API_DESCRIPTION,
    version=__version__,
    # dependencies=[Depends(setup_audit_listeners)],
    swagger_ui_oauth2_redirect_url='/docs/oauth2-redirect',
    swagger_ui_init_oauth={
        'usePkceWithAuthorizationCodeGrant': True,
        'clientId': AZURE_AD_FRONTEND_CLIENT_ID,
    },
)

azure_scheme = MultiTenantAzureAuthorizationCodeBearer(
    app_client_id=AZURE_AD_FRONTEND_CLIENT_ID,
    scopes={
        f"{AZURE_AD_AUDIENCE}/api.access": "api.access",
    },
    validate_iss=False
)

app.include_router(chats.router, dependencies=[Security(azure_scheme)], tags=["Chat"])
app.include_router(agent.router)


@app.on_event('startup')
async def load_config() -> None:
    """
    Load OpenID config on startup.
    """
    await azure_scheme.openid_config.load_config()