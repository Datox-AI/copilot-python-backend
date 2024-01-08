from dotenv import load_dotenv
import os

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.openapi.docs import get_swagger_ui_html, get_swagger_ui_oauth2_redirect_html
import os

load_dotenv()  # Load environment variables

AZURE_AD_INSTANCE = os.getenv("AZURE_AD_INSTANCE")
AZURE_AD_TENANT_ID = os.getenv("AZURE_AD_TENANT_ID")
AZURE_AD_AUDIENCE = os.getenv("AZURE_AD_AUDIENCE")
AZURE_AD_FRONTEND_CLIENT_ID = os.getenv('AZURE_AD_FRONTEND_CLIENT_ID')


def custom_openapi(app: FastAPI):
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="My API",
        version="v1",
        description="This is a very custom OpenAPI schema",
        routes=app.routes,
    )

    if 'components' not in openapi_schema:
        openapi_schema['components'] = {'securitySchemes': {}}
    
    if 'securitySchemes' not in openapi_schema['components']:
        openapi_schema["components"]["securitySchemes"] = {}

    oauth2_scheme = {
        "type": "oauth2",
        "flows": {
            "implicit": {
                "authorizationUrl": f"{AZURE_AD_INSTANCE}{AZURE_AD_TENANT_ID}/oauth2/v2.0/authorize",
                "scopes": {f"{AZURE_AD_AUDIENCE}/api.access": "Access the API"},
                "tokenUrl": f"{AZURE_AD_INSTANCE}{AZURE_AD_TENANT_ID}/oauth2/v2.0/token",
            }
        }
    }

    openapi_schema["components"]["securitySchemes"]["oauth2"] = oauth2_scheme
    openapi_schema["security"] = [{"oauth2": [f"{AZURE_AD_AUDIENCE}/api.access"]}]

    app.openapi_schema = openapi_schema