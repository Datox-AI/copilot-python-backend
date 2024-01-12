<<<<<<< HEAD
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
=======
from typing import Annotated
from fastapi import Depends, FastAPI
from app.schemas.identity.current_user import CurrentUser
>>>>>>> e26444a36e58f222100773c7b73ba5dd51956bbf

from .const import (
    OPEN_API_DESCRIPTION,
    OPEN_API_TITLE,
)

from .version import __version__
from app.models.base_models import setup_audit_listeners
from app.routers import (
    chats, agent
)

<<<<<<< HEAD

load_dotenv() 

AZURE_AD_INSTANCE = os.getenv("AZURE_AD_INSTANCE")
AZURE_AD_TENANT_ID = os.getenv("AZURE_AD_TENANT_ID")
AZURE_AD_AUDIENCE = os.getenv("AZURE_AD_AUDIENCE")
AZURE_AD_FRONTEND_CLIENT_ID = os.getenv('AZURE_AD_FRONTEND_CLIENT_ID')
=======
from app.shared.auth import (
    azure_scheme, AZURE_AD_FRONTEND_CLIENT_ID, current_user
)
>>>>>>> e26444a36e58f222100773c7b73ba5dd51956bbf

app = FastAPI(
    title=OPEN_API_TITLE,
    description=OPEN_API_DESCRIPTION,
    version=__version__,
<<<<<<< HEAD
    # dependencies=[Depends(setup_audit_listeners)],
=======
>>>>>>> e26444a36e58f222100773c7b73ba5dd51956bbf
    swagger_ui_oauth2_redirect_url='/docs/oauth2-redirect',
    swagger_ui_init_oauth={
        'usePkceWithAuthorizationCodeGrant': True,
        'clientId': AZURE_AD_FRONTEND_CLIENT_ID,
    },
    dependencies=[Depends(current_user)]
)

<<<<<<< HEAD
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
=======
@app.on_event("startup")
>>>>>>> e26444a36e58f222100773c7b73ba5dd51956bbf
async def load_config() -> None:
    """
    Load OpenID config on startup.
    """
    await azure_scheme.openid_config.load_config()
    
app.include_router(chats.router)