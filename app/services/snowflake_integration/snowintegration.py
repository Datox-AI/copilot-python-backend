from typing import Annotated
from fastapi import Depends
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from urllib.parse import urlencode
import httpx
from httpx import HTTPStatusError, NetworkError, ConnectTimeout, ReadTimeout
import snowflake.connector
from snowflake.connector.errors import DatabaseError, ProgrammingError, InterfaceError, OperationalError
from pydantic import BaseModel
from sqlalchemy.orm import Session
from httpx import HTTPStatusError, NetworkError, ConnectTimeout, ReadTimeout
from fastapi import HTTPException
from app.models.maindb.snowflake_identifier import SnowflakeIdentifier, SnowflakeWarehouse
from app.backend.session import create_maindb_session
from app.shared.auth.azure_scheme import current_user
from app.schemas.identity.current_user import CurrentUser
from app.schemas.snowintegration import OAuthConfig, SnowflakeOauthMapper
import uuid
import logging

app = FastAPI()


REDIRECT_URI = "https://ashy-wave-0c6d0ea0f-dev.eastus2.4.azurestaticapps.net/callback/snowflake"


class SnowflakeIntegrationService:
    def __init__(
        self,
        session: Annotated[Session, Depends(create_maindb_session)],
        user: Annotated[CurrentUser, Depends(current_user)],
    ) -> None:
        self.session = session
        self.user = user

    def handle_common_errors(self, exception):
        if isinstance(exception, HTTPStatusError):
            # logging.error(f"HTTP status error occurred: {exception}")
            raise HTTPException(status_code=500, detail="HTTP status error occurred")
        elif isinstance(exception, NetworkError):
            # logging.error(f"Network error occurred: {exception}")
            raise HTTPException(status_code=500, detail="Network error occurred")
        elif isinstance(exception, (ConnectTimeout, ReadTimeout)):
            # logging.error(f"Timeout error occurred: {exception}")
            raise HTTPException(status_code=500, detail="Timeout error occurred")
        else:  # General exception
            print(exception)
            # logging.error(f"Unexpected error: {exception}")
            raise HTTPException(status_code=500, detail="Unexpected error occurred")

    def _get_snowflake_identifier_obj(self):
        existing_snowflake_identifier_obj = (
            self.session.query(SnowflakeIdentifier).filter(SnowflakeIdentifier.user_id == self.user.user_id).first()
        )
        if not existing_snowflake_identifier_obj:
            raise HTTPException(status_code=404, detail="User does not have snowflake identifier object")

        if existing_snowflake_identifier_obj:
            selected_warehouse_obj = (
                self.session.query(SnowflakeWarehouse)
                .filter(
                    SnowflakeWarehouse.identifier == existing_snowflake_identifier_obj,
                    SnowflakeWarehouse.selected == True,
                )
                .first()
            )
        else:
            selected_warehouse_obj = None
        return existing_snowflake_identifier_obj, selected_warehouse_obj

    # Endpoint to initialize OAuth configuration
    def init_oauth_logic(self, config: OAuthConfig):
        authorization_endpoint = config.token_endpoint.replace("token-request", "authorize")
        existing_snowflake_identifier_obj = (
            self.session.query(SnowflakeIdentifier).filter(SnowflakeIdentifier.user_id == self.user.user_id).first()
        )
        if existing_snowflake_identifier_obj:
            raise HTTPException(status_code=404, detail="User has already snowflake identifier object")

        snowflake_identifier_obj = SnowflakeIdentifier(
            id=uuid.uuid4(),
            user_id=self.user.user_id,
            account_identifier=config.account_identifier,
            client_id=config.client_id,
            client_secret=config.client_secret,
            token_endpoint=config.token_endpoint,
            authorization_endpoint=authorization_endpoint,
        )
        warehouse_obj = SnowflakeWarehouse(
            id=uuid.uuid4(), name=config.warehouse, identifier=snowflake_identifier_obj, selected=True
        )

        self.session.add(snowflake_identifier_obj)
        self.session.add(warehouse_obj)
        self.session.commit()
        params = {
            "response_type": "code",
            "client_id": config.client_id,
            "redirect_uri": REDIRECT_URI,
            "account": config.account_identifier,
        }
        authorization_url = f"{authorization_endpoint}?{urlencode(params)}"

        return {"authorization_url": authorization_url}

    def get_oauth_logic(self):
        existing_snowflake_identifier_obj, selected_warehouse_obj = self._get_snowflake_identifier_obj()

        authorization_endpoint = existing_snowflake_identifier_obj.token_endpoint.replace("token-request", "authorize")
        params = {
            "response_type": "code",
            "client_id": existing_snowflake_identifier_obj.client_id,
            "redirect_uri": REDIRECT_URI,
            "account": existing_snowflake_identifier_obj.account_identifier,
        }
        authorization_url = f"{authorization_endpoint}?{urlencode(params)}"

        return SnowflakeOauthMapper.map_to_oauth_response(
            snowflake_identifier=existing_snowflake_identifier_obj,
            warehouse_obj=selected_warehouse_obj,
            authorization_url=authorization_url,
        )

    def update_oauth_logic(self, config):
        existing_snowflake_identifier_obj = self._get_snowflake_identifier_obj()[0]

        authorization_endpoint = config.token_endpoint.replace("token-request", "authorize")
        existing_snowflake_identifier_obj.account_identifier = config.account_identifier
        existing_snowflake_identifier_obj.client_id = config.client_id
        existing_snowflake_identifier_obj.client_secret = config.client_secret
        existing_snowflake_identifier_obj.token_endpoint = config.token_endpoint
        existing_snowflake_identifier_obj.authorization_endpoint = authorization_endpoint
        self.session.commit()
        params = {
            "response_type": "code",
            "client_id": config.client_id,
            "redirect_uri": REDIRECT_URI,
            "account": config.account_identifier,
        }
        authorization_url = f"{authorization_endpoint}?{urlencode(params)}"

        return {"authorization_url": authorization_url}

    def delete_oauth_logic(self):
        existing_snowflake_identifier_obj = self._get_snowflake_identifier_obj()[0]
        self.session.delete(existing_snowflake_identifier_obj)
        self.session.commit()

    async def oauth_callback_logic(self, code: str):
        if not code:
            raise HTTPException(status_code=400, detail="Authorization code not provided")
        token_response = await self.exchange_code_for_token(code)

        try:
            if "access_token" not in token_response:
                raise HTTPException(status_code=400, detail="Access token not in response")
            return token_response
        except Exception as e:
            self.handle_common_errors(e)

    # Exchanges an authorization code for an access token
    async def exchange_code_for_token(self, code: str):
        snowflake_identifier_obj = self._get_snowflake_identifier_obj()[0]
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    snowflake_identifier_obj.token_endpoint,
                    data={
                        "grant_type": "authorization_code",
                        "code": code,
                        "redirect_uri": REDIRECT_URI,
                        "client_id": snowflake_identifier_obj.client_id,
                        "client_secret": snowflake_identifier_obj.client_secret,
                    },
                )

            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise HTTPException(status_code=400, detail="Code is invalid or outdated")

    # Refresh access token logic
    async def refresh_access_token_logic(self, refresh_token: str):
        snowflake_identifier_obj = self._get_snowflake_identifier_obj()
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    snowflake_identifier_obj.token_endpoint,
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": refresh_token,
                        "client_id": snowflake_identifier_obj.client_id,
                        "client_secret": snowflake_identifier_obj.client_secret,
                    },
                )
                response.raise_for_status()
                return response.json()

        except Exception as e:
            self.handle_common_errors(e)

    # Creates a connection to Snowflake
    def create_snowflake_connection(self, oauth_token: str, snowflake_account: str):
        ctx = snowflake.connector.connect(account=snowflake_account, authenticator="oauth", token=oauth_token)
        return ctx

    def _create_warehouse(self, warehouse_name):
        snowflake_identifier_obj, selected_warehouse_obj = self._get_snowflake_identifier_obj()

        warehouse_obj = SnowflakeWarehouse(name=warehouse_name, identifier=snowflake_identifier_obj, selected=True)
        # unselecting
        selected_warehouse_obj.selected = False
        self.session.add(warehouse_obj)
        self.session.commit()

    # Endpoint to list data warehouses
    def list_data_warehouses_logic(self, token: str):
        snowflake_identifier_obj = self._get_snowflake_identifier_obj()[0]

        ctx = self.create_snowflake_connection(token, snowflake_identifier_obj.account_identifier)
        if ctx is None:
            # Handle the error appropriately
            raise ConnectionError("Failed to establish a connection to Snowflake.")
        cursor = ctx.cursor()
        try:
            cursor.execute("SHOW WAREHOUSES")
            warehouses = cursor.fetchall()
            # Assuming the first column contains the warehouse names
            warehouse_names = [wh[0] for wh in warehouses]  # Adjust the index if needed
            return {"data_warehouses": warehouse_names}
        finally:
            cursor.close()
            ctx.close()

    # Endpoint to select a data warehouse
    def select_warehouse_logic(self, token: str, warehouse_name: str):
        try:
            # Hypothetical method to select the warehouse
            self._create_warehouse(warehouse_name)
        except PermissionError:
            raise PermissionError("Insufficient permissions to select the warehouse")
        except Exception as e:
            print(f"Unexpected error: {e}")
            raise RuntimeError("An unexpected error occurred while selecting the warehouse")

        return {"message": f"Data warehouse '{warehouse_name}' selected"}

    # Modified endpoint to list databases using the selected data warehouse
    def list_databases_logic(self, token: str):
        snowflake_identifier_obj, selected_warehouse_obj = self._get_snowflake_identifier_obj()

        ctx = self.create_snowflake_connection(token, snowflake_identifier_obj.account_identifier)
        cursor = ctx.cursor()
        try:
            cursor.execute(f"USE WAREHOUSE {selected_warehouse_obj.name}")
            cursor.execute("SHOW DATABASES")
            databases = cursor.fetchall()
            return {"databases": [db[1] for db in databases]}
        finally:
            cursor.close()
            ctx.close()

    def get_schemas_logic(self, token: str, db_name: str):
        snowflake_identifier_obj, selected_warehouse_obj = self._get_snowflake_identifier_obj()

        ctx = self.create_snowflake_connection(token, snowflake_identifier_obj.account_identifier)
        cursor = ctx.cursor()
        try:
            cursor.execute(f"USE WAREHOUSE {selected_warehouse_obj.name}")
            cursor.execute(f"SHOW SCHEMAS IN DATABASE {db_name}")
            schemas = cursor.fetchall()
            return {"schemas": [schema[1] for schema in schemas]}
        finally:
            cursor.close()
            ctx.close()

    # Endpoint to select a schema and check separately for the existence of tables and views
    def select_schema_logic(self, token: str, db_name: str, schema_name: str):
        snowflake_identifier_obj, selected_warehouse_obj = self._get_snowflake_identifier_obj()

        try:
            conn = self.create_snowflake_connection(token, snowflake_identifier_obj.account_identifier)
            cursor = conn.cursor()

            try:
                cursor.execute(f"USE WAREHOUSE {selected_warehouse_obj.name}")
                cursor.execute(f"SHOW TABLES IN {db_name}.{schema_name}")
                tables_status = len(cursor.fetchall()) > 0

                cursor.execute(f"SHOW VIEWS IN {db_name}.{schema_name}")
                views_status = len(cursor.fetchall()) > 0

                return {"message": f"Schema '{schema_name}' selected", "tables": tables_status, "views": views_status}

            finally:
                if "conn" in locals() and conn is not None:
                    conn.close()
        except Exception as e:
            self.handle_common_errors(e)

    # Endpoint to list tables of a specific schema in a Snowflake database
    def get_tables_logic(self, token: str, db_name: str, schema_name: str):
        snowflake_identifier_obj, selected_warehouse_obj = self._get_snowflake_identifier_obj()

        try:
            conn = self.create_snowflake_connection(token, snowflake_identifier_obj.account_identifier)
            cursor = conn.cursor()

            try:
                cursor.execute(f"USE WAREHOUSE {selected_warehouse_obj.name}")
                cursor.execute(f"SHOW TABLES IN {db_name}.{schema_name}")
                tables = cursor.fetchall()
                return {"tables": [table[1] for table in tables]}
            finally:
                cursor.close()
        except Exception as e:
            self.handle_common_errors(e)

    # Endpoint to list views of a specific schema in a Snowflake database
    def change_default_role_logic(self, new_role: str, token: str):
        snowflake_identifier_obj = self._get_snowflake_identifier_obj()
        if not snowflake_identifier_obj:
            raise HTTPException(status_code=400, detail="User does not have snowflake identifier object")

        try:
            conn = self.create_snowflake_connection(token, snowflake_identifier_obj.account_identifier)
            cursor = conn.cursor()
            # Get the current user's username
            cursor.execute("SELECT CURRENT_USER();")
            current_username = cursor.fetchone()[0]

            # Changing the default role for the current user in Snowflake
            try:
                cursor.execute(f"ALTER USER {current_username} SET DEFAULT_ROLE = '{new_role}'")
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to change default role: {e}")

            return {"detail": f"Default role for user '{current_username}' changed to '{new_role}' successfully"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
        finally:
            cursor.close()
            conn.close()

    def get_views_logic(self, token: str, db_name: str, schema_name: str):
        snowflake_identifier_obj, selected_warehouse_obj = self._get_snowflake_identifier_obj()

        try:
            conn = self.create_snowflake_connection(token, snowflake_identifier_obj.account_identifier)
            cursor = conn.cursor()

            try:
                cursor.execute(f"USE WAREHOUSE {selected_warehouse_obj.name}")
                cursor.execute(f"SHOW VIEWS IN {db_name}.{schema_name}")
                views = cursor.fetchall()
                return {"views": [view[1] for view in views]}
            finally:
                cursor.close()
        except Exception as e:
            self.handle_common_errors(e)

    # Endpoint to list columns of a specific table or view in a Snowflake database, including name and type

    def get_columns_logic(self, token: str, db_name: str, schema_name: str, table_or_view_name: str):
        snowflake_identifier_obj, selected_warehouse_obj = self._get_snowflake_identifier_obj()

        try:
            conn = self.create_snowflake_connection(token, snowflake_identifier_obj.account_identifier)
            cursor = conn.cursor()

            try:
                cursor.execute(f"USE WAREHOUSE {selected_warehouse_obj.name}")
                cursor.execute(f"DESCRIBE TABLE {db_name}.{schema_name}.{table_or_view_name}")
                columns = cursor.fetchall()
                # Format the columns data to include only name and type. Adjust indices based on Snowflake's response format
                columns_data = [{"name": col[0], "type": col[1]} for col in columns]
                return {"columns": columns_data}
            finally:
                cursor.close()
        except Exception as e:
            self.handle_common_errors(e)

    # Endpoint to preview data from a specific table or view in a Snowflake database
    def preview_data_logic(self, token: str, db_name: str, schema_name: str, table_or_view_name: str):
        snowflake_identifier_obj, selected_warehouse_obj = self._get_snowflake_identifier_obj()

        try:
            conn = self.create_snowflake_connection(token, snowflake_identifier_obj.account_identifier)
            cursor = conn.cursor()

            try:
                cursor.execute(f"USE WAREHOUSE {selected_warehouse_obj.name}")
                query = f"SELECT * FROM {db_name}.{schema_name}.{table_or_view_name} LIMIT 10"
                cursor.execute(query)

                # Fetch column names
                column_names = [desc[0] for desc in cursor.description]

                # Fetch data and format rows
                data_preview = []
                for row in cursor.fetchall():
                    formatted_row = {
                        col_name: (value if value is not None else "{none}")
                        for col_name, value in zip(column_names, row)
                    }
                    data_preview.append(formatted_row)

                return {"data_preview": data_preview}
            finally:
                cursor.close()
        except Exception as e:
            self.handle_common_errors(e)

    # list available roles
    def get_available_roles_logic(self, token: str):
        snowflake_identifier_obj = self._get_snowflake_identifier_obj()[0]

        try:
            conn = self.create_snowflake_connection(token, snowflake_identifier_obj.account_identifier)
            cursor = conn.cursor()

            try:
                cursor.execute("SELECT CURRENT_AVAILABLE_ROLES();")
                roles = cursor.fetchall()

                available_roles = [role[0] for role in roles]

                return {"available_roles": available_roles}
            finally:
                cursor.close()
                conn.close()
        except Exception as e:
            self.handle_common_errors(e)
