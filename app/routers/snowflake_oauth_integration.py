from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.snowintegration import (
    init_oauth_service,
    oauth_callback_service,
    list_data_warehouses_service,
    select_warehouse_service,
    list_databases_service,
    get_schemas_service,
    get_tables_service,
    get_views_service,
    get_columns_service,
    preview_data_service,

)

router = APIRouter()

# Pydantic model for OAuth configuration
class OAuthConfig(BaseModel):
    account_identifier: str
    client_id: str
    client_secret: str
    token_endpoint: str
    redirect_uri: str

# Initialize OAuth configuration
@router.post("/init_oauth")
def init_oauth(config: OAuthConfig):
    return init_oauth_service(config)

# Callback endpoint for OAuth flow
@router.get("/callback")
async def oauth_callback(code: str):
    return await oauth_callback_service(code)

# List data warehouses
@router.get("/data_warehouses")
def list_data_warehouses(token: str):
    return list_data_warehouses_service(token)

# Select a data warehouse
@router.post("/select_warehouse")
def select_warehouse(token: str, warehouse_name: str):
    return select_warehouse_service(token, warehouse_name)

# List databases
@router.get("/databases")
def list_databases(token: str):
    return list_databases_service(token)

# Get schemas
@router.get("/schemas/{db_name}")
def get_schemas(token: str, db_name: str):
    return get_schemas_service(token, db_name)

# Get tables
@router.get("/tables/{db_name}/{schema_name}")
def get_tables(token: str, db_name: str, schema_name: str):
    return get_tables_service(token, db_name, schema_name)

# Get views
@router.get("/views/{db_name}/{schema_name}")
def get_views(token: str, db_name: str, schema_name: str):
    return get_views_service(token, db_name, schema_name)

# List columns of a specific table or view in a Snowflake database
@router.get("/columns/{db_name}/{schema_name}/{table_or_view_name}")
def get_columns(token: str, db_name: str, schema_name: str, table_or_view_name: str):
    return get_columns_service(token, db_name, schema_name, table_or_view_name)

# Preview data from a specific table or view in a Snowflake database
@router.get("/preview_data/{db_name}/{schema_name}/{table_or_view_name}")
def preview_data(token: str, db_name: str, schema_name: str, table_or_view_name: str):
    return preview_data_service(token, db_name, schema_name, table_or_view_name)
