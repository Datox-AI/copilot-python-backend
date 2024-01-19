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
   

'''
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from urllib.parse import urlencode
import httpx
from fastapi import APIRouter, HTTPException
import snowflake.connector
from fastapi.middleware.cors import CORSMiddleware

router = APIRouter()
app = FastAPI()



# Pydantic model for OAuth configuration
class OAuthConfig(BaseModel):
    account_identifier: str
    client_id: str
    client_secret: str
    token_endpoint: str
    redirect_uri: str
    manual_warehouse: str  # New field for manual warehouse entry
    
# Global variables for OAuth and Snowflake details
OAUTH_CLIENT_ID = 'your_oauth_client_id'  # Replace with your OAuth client ID
OAUTH_CLIENT_SECRET = 'your_oauth_client_secret'  # Replace with your OAuth client secret
AUTHORIZATION_ENDPOINT = 'your_authorization_endpoint'  # Replace with your authorization endpoint
TOKEN_ENDPOINT = 'your_token_endpoint'  # Replace with your token endpoint
SNOWFLAKE_ACCOUNT = 'your_snowflake_account'  # Replace with your Snowflake account
REDIRECT_URI = "https://copilot.datox.ai/integration/2"  # Replace with your redirect URI
SELECTED_WAREHOUSE = None  # Variable to store the selected data warehouse

# Constructs the URL for OAuth authorization
def construct_authorization_url():
    params = {
        "response_type": "code",
        "client_id": OAUTH_CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "account": SNOWFLAKE_ACCOUNT
    }
    return f"{AUTHORIZATION_ENDPOINT}?{urlencode(params)}"

# Endpoint to initialize OAuth configuration
@router.post("/init_oauth")
def init_oauth(config: OAuthConfig):
    global SNOWFLAKE_ACCOUNT, OAUTH_CLIENT_ID, OAUTH_CLIENT_SECRET, AUTHORIZATION_ENDPOINT, TOKEN_ENDPOINT, REDIRECT_URI, SELECTED_WAREHOUSE
    SNOWFLAKE_ACCOUNT = config.account_identifier
    OAUTH_CLIENT_ID = config.client_id
    OAUTH_CLIENT_SECRET = config.client_secret
    TOKEN_ENDPOINT = config.token_endpoint
    AUTHORIZATION_ENDPOINT = config.token_endpoint.replace("token-request", "authorize")
    REDIRECT_URI = config.redirect_uri
    SELECTED_WAREHOUSE = config.manual_warehouse  # Set the manually entered warehouse
    authorization_url = construct_authorization_url()
    return {"authorization_url": authorization_url}

# Callback endpoint for OAuth flow
@router.get("/callback")
async def oauth_callback(code: str):
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code not provided")
    try:
        token_response = await exchange_code_for_token(code)
        if 'access_token' not in token_response:
            raise HTTPException(status_code=400, detail="Access token not in response")
    except Exception as e:
        print(f"Error in exchange_code_for_token: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    access_token = token_response['access_token']
    return {"access_token": access_token}

# Exchanges an authorization code for an access token
async def exchange_code_for_token(code: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            TOKEN_ENDPOINT,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": REDIRECT_URI,
                "client_id": OAUTH_CLIENT_ID,
                "client_secret": OAUTH_CLIENT_SECRET
            }
        )
        response.raise_for_status()
        return response.json()

# Creates a connection to Snowflake
def create_snowflake_connection(oauth_token: str):
    ctx = snowflake.connector.connect(
        account=SNOWFLAKE_ACCOUNT,
        authenticator='oauth',
        token=oauth_token
    )
    return ctx

# New endpoint to list all warehouses
@router.get("/list_warehouses")
def list_all_warehouses(token: str):
    ctx = create_snowflake_connection(token)
    cursor = ctx.cursor()
    try:
        cursor.execute("SHOW WAREHOUSES")
        warehouses = cursor.fetchall()
        warehouse_names = [wh[0] for wh in warehouses]
        return {"warehouses": warehouse_names}
    finally:
        cursor.close()
        ctx.close()

# New endpoint to select a warehouse from the list
@router.post("/select_warehouse_from_list")
def select_warehouse_from_list(token: str, warehouse_name: str):
    global SELECTED_WAREHOUSE
    SELECTED_WAREHOUSE = warehouse_name
    return {"message": f"Warehouse '{warehouse_name}' selected"}


# Modified endpoint to list databases using the selected data warehouse
@router.get("/databases")
def list_databases(token: str):
    if not SELECTED_WAREHOUSE:
        raise HTTPException(status_code=400, detail="No data warehouse selected")
    conn = create_snowflake_connection(token)
    cursor = conn.cursor()
    try:
        cursor.execute(f"USE WAREHOUSE {SELECTED_WAREHOUSE}")
        cursor.execute("SHOW DATABASES")
        databases = cursor.fetchall()
        return {"databases": [db[1] for db in databases]}
    finally:
        cursor.close()
        conn.close()



# Endpoint to list schemas of a specific database in Snowflake
@router.get("/schemas/{db_name}")
def get_schemas(token: str, db_name: str):
    if not SELECTED_WAREHOUSE:
        raise HTTPException(status_code=400, detail="No data warehouse selected")

    ctx = create_snowflake_connection(token)
    cursor = ctx.cursor()
    try:
        cursor.execute(f"USE WAREHOUSE {SELECTED_WAREHOUSE}")
        cursor.execute(f"SHOW SCHEMAS IN DATABASE {db_name}")
        schemas = cursor.fetchall()
        return {"schemas": [schema[1] for schema in schemas]}
    finally:
        cursor.close()
        ctx.close()


@router.get("/select_schema")
def select_schema(token: str, db_name: str, schema_name: str):
    global SELECTED_SCHEMA
    SELECTED_SCHEMA = schema_name

    ctx = create_snowflake_connection(token)
    cursor = ctx.cursor()
    try:
        cursor.execute(f"USE WAREHOUSE {SELECTED_WAREHOUSE}")

        # Check if there are tables in the schema
        cursor.execute(f"SHOW TABLES IN {db_name}.{schema_name}")
        tables_status = len(cursor.fetchall()) > 0

        # Check if there are views in the schema
        cursor.execute(f"SHOW VIEWS IN {db_name}.{schema_name}")
        views_status = len(cursor.fetchall()) > 0

        return {
            "message": f"Schema '{schema_name}' selected",
            "tables": tables_status,
            "views": views_status
        }
    finally:
        cursor.close()
        ctx.close()



# Endpoint to list tables of a specific schema in a Snowflake database
@router.get("/tables/{db_name}/{schema_name}")
def get_tables(token: str, db_name: str, schema_name: str):
    if not SELECTED_WAREHOUSE:
        raise HTTPException(status_code=400, detail="No data warehouse selected")

    ctx = create_snowflake_connection(token)
    cursor = ctx.cursor()
    try:
        cursor.execute(f"USE WAREHOUSE {SELECTED_WAREHOUSE}")
        cursor.execute(f"SHOW TABLES IN {db_name}.{schema_name}")
        tables = cursor.fetchall()
        return {"tables": [table[1] for table in tables]}
    finally:
        cursor.close()
        ctx.close()


# Endpoint to list views of a specific schema in a Snowflake database
@router.get("/views/{db_name}/{schema_name}")
def get_views(token: str, db_name: str, schema_name: str):
    if not SELECTED_WAREHOUSE:
        raise HTTPException(status_code=400, detail="No data warehouse selected")

    ctx = create_snowflake_connection(token)
    cursor = ctx.cursor()
    try:
        cursor.execute(f"USE WAREHOUSE {SELECTED_WAREHOUSE}")
        cursor.execute(f"SHOW VIEWS IN {db_name}.{schema_name}")
        views = cursor.fetchall()
        return {"views": [view[1] for view in views]}
    finally:
        cursor.close()
        ctx.close()

# Endpoint to list columns of a specific table or view in a Snowflake database, including name and type
@router.get("/columns/{db_name}/{schema_name}/{table_or_view_name}")
def get_columns_and_row_count(token: str, db_name: str, schema_name: str, table_or_view_name: str):
    if not SELECTED_WAREHOUSE:
        raise HTTPException(status_code=400, detail="No data warehouse selected")

    ctx = create_snowflake_connection(token)
    cursor = ctx.cursor()

    try:
        cursor.execute(f"USE WAREHOUSE {SELECTED_WAREHOUSE}")
        cursor.execute(f"DESCRIBE TABLE {db_name}.{schema_name}.{table_or_view_name}")
        columns = cursor.fetchall()
        columns_data = [{"name": col[0], "type": col[1]} for col in columns]

        cursor.execute(f"SHOW TABLES LIKE '{table_or_view_name}' IN SCHEMA {db_name}.{schema_name}")
        is_table = len(cursor.fetchall()) > 0

        row_count = None
        if is_table:
            cursor.execute(f"SELECT COUNT(*) FROM {db_name}.{schema_name}.{table_or_view_name}")
            row_count = cursor.fetchone()[0]

        return {
            "columns": columns_data,
            "row_count": row_count
        }
    finally:
        cursor.close()
        ctx.close()


# Endpoint to preview data from a specific table or view in a Snowflake database
@router.get("/preview_data/{db_name}/{schema_name}/{table_or_view_name}")
def preview_data(token: str, db_name: str, schema_name: str, table_or_view_name: str):
    if not SELECTED_WAREHOUSE:
        raise HTTPException(status_code=400, detail="No data warehouse selected")

    ctx = create_snowflake_connection(token)
    cursor = ctx.cursor()
    try:
        cursor.execute(f"USE WAREHOUSE {SELECTED_WAREHOUSE}")
        query = f"SELECT * FROM {db_name}.{schema_name}.{table_or_view_name} LIMIT 10"
        cursor.execute(query)

        # Fetch column names
        column_names = [desc[0] for desc in cursor.description]

        # Fetch data and format rows
        data_preview = []
        for row in cursor.fetchall():
            formatted_row = {col_name: (value if value is not None else "{none}")
                             for col_name, value in zip(column_names, row)}
            data_preview.append(formatted_row)

        return {"data_preview": data_preview}
    finally:
        cursor.close()
        ctx.close()

@router.get("/preview_data/{db_name}/{schema_name}/{table_or_view_name}")
def preview_data_and_counts(token: str, db_name: str, schema_name: str, table_or_view_name: str):
    if not SELECTED_WAREHOUSE:
        raise HTTPException(status_code=400, detail="No data warehouse selected")

    ctx = create_snowflake_connection(token)
    cursor = ctx.cursor()

    try:
        cursor.execute(f"USE WAREHOUSE {SELECTED_WAREHOUSE}")
        query = f"SELECT * FROM {db_name}.{schema_name}.{table_or_view_name} LIMIT 10"
        cursor.execute(query)

        # Fetch column names for the preview
        column_names = [desc[0] for desc in cursor.description]
        column_count = len(column_names)

        # Fetch data and format rows for the preview
        data_preview = [{col_name: (value if value is not None else "{none}")
                         for col_name, value in zip(column_names, row)}
                        for row in cursor.fetchall()]

        # Determine if it's a table to get row count
        cursor.execute(f"SHOW TABLES LIKE '{table_or_view_name}' IN SCHEMA {db_name}.{schema_name}")
        is_table = len(cursor.fetchall()) > 0

        row_count = None
        if is_table:
            cursor.execute(f"SELECT COUNT(*) FROM {db_name}.{schema_name}.{table_or_view_name}")
            row_count = cursor.fetchone()[0]

        return {
            "data_preview": data_preview,
            "column_count": column_count,
            "row_count": row_count
        }
    finally:
        cursor.close()
        ctx.close()
'''