from fastapi import FastAPI, HTTPException
from urllib.parse import urlencode
from fastapi.middleware.cors import CORSMiddleware
from fastapi import APIRouter
from pydantic import BaseModel
from app.services.snowflake_integration.snowintegration import (
    init_oauth_logic,
    oauth_callback_logic,
    list_data_warehouses_logic,
    select_warehouse_logic,
    list_databases_logic,
    get_schemas_logic,
    select_schema_logic,
    get_tables_logic,
    get_views_logic,
    get_columns_logic,
    preview_data_logic
)

router = APIRouter()


app = FastAPI()


# Pydantic model for OAuth configuration
class OAuthConfig(BaseModel):
    account_identifier: str
    client_id: str
    client_secret: str
    token_endpoint: str
    redirect_uri: str


# Endpoint to initialize OAuth configuration
@router.post("/init_oauth")
def init_oauth(config: OAuthConfig):
    return init_oauth_logic(config)

@router.get("/callback")
async def oauth_callback(code: str):
    return await oauth_callback_logic(code)

# Endpoint to list data warehouses
@router.get("/data_warehouses")
def list_data_warehouses(token: str):
    return list_data_warehouses_logic (token)

# Endpoint to select a data warehouse
@router.post("/select_warehouse")
def select_warehouse(token: str, warehouse_name: str):
    return select_warehouse_logic (token, warehouse_name)

# Modified endpoint to list databases using the selected data warehouse
@router.get("/databases")
def list_databases(token: str):
    return list_databases_logic(token)


# Endpoint to list schemas of a specific database in Snowflake
@router.get("/schemas/{db_name}")
def get_schemas(token: str, db_name: str):
    return {"schemas": get_schemas_logic(token, db_name)}

# Endpoint to select a schema and check separately for the existence of tables and views
@router.get("/select_schema")
def select_schema(token: str, db_name: str, schema_name: str):
    return select_schema_logic(token, db_name, schema_name)


# Endpoint to list tables of a specific schema in a Snowflake database
@router.get("/tables/{db_name}/{schema_name}")
def get_tables(token: str, db_name: str, schema_name: str):
    return get_tables_logic(token, db_name, schema_name)


# Endpoint to list views of a specific schema in a Snowflake database
@router.get("/views/{db_name}/{schema_name}")
def get_views(token: str, db_name: str, schema_name: str):
    return get_views_logic(token, db_name, schema_name)


# Endpoint to list columns of a specific table or view in a Snowflake database, including name and type
@router.get("/columns/{db_name}/{schema_name}/{table_or_view_name}")
def get_columns(token: str, db_name: str, schema_name: str, table_or_view_name: str):
     return get_columns_logic(token, db_name, schema_name, table_or_view_name)

@router.get("/preview/{db_name}/{schema_name}/{table_or_view_name}")
def preview_data(token: str, db_name: str, schema_name: str, table_or_view_name: str):
    return {"data_preview": preview_data_logic(token, db_name, schema_name, table_or_view_name)}
   