import os

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_pagination import add_pagination

from app.routers import analytics_agent, chats, files, user_messages, rag_agent, snow_router
from app.shared.auth import AZURE_AD_FRONTEND_CLIENT_ID, azure_scheme
from .const import OPEN_API_DESCRIPTION, OPEN_API_TITLE
from .version import __version__

load_dotenv()

app = FastAPI(
    title=OPEN_API_TITLE,
    description=OPEN_API_DESCRIPTION,
    version=__version__,
    swagger_ui_oauth2_redirect_url="/docs/oauth2-redirect",
    swagger_ui_init_oauth={
        "usePkceWithAuthorizationCodeGrant": True,
        "clientId": AZURE_AD_FRONTEND_CLIENT_ID,
    },
    # dependencies=[Depends(current_user)]
)
# Adding pagination to an app
add_pagination(app)

# Adding CORS middleware
origins = os.environ["ALLOWED_ORIGINS"].split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Adding routers
app.include_router(chats.router)
app.include_router(analytics_agent.router)
app.include_router(rag_agent.router)
app.include_router(files.router)
app.include_router(user_messages.router)
app.include_router(snow_router.router)


@app.on_event("startup")
async def load_config() -> None:
    """
    Load OpenID config on startup.
    """
    await azure_scheme.openid_config.load_config()


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="localhost",
        port=7202,
        ssl_certfile="./SSL/domain.crt",
        ssl_keyfile="./SSL/domain.key",
    )
