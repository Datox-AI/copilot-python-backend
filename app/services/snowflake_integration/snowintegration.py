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
import datetime

from app.models.maindb.snowflake_identifier import SnowflakeIdentifier
from app.backend.session import create_maindb_session
from app.shared.auth.azure_scheme import current_user
from app.schemas.identity.current_user import CurrentUser
from app.schemas.snowintegration import OAuthConfig, SnowflakeOauthMapper


app = FastAPI()


REDIRECT_URI = "https://copilot.datox.ai/integration/2" 


class SnowflakeIntegrationService:
    def __init__(
        self,
        session: Annotated[Session, Depends(create_maindb_session)],
        user: Annotated[CurrentUser, Depends(current_user)],

    ) -> None:
        self.session = session
        self.user = user 

    # Endpoint to initialize OAuth configuration
    def init_oauth_logic(self, config: OAuthConfig):
        authorization_endpoint = config.token_endpoint.replace("token-request", "authorize")
        existing_snowflake_identfier_obj = self._get_snowflake_identifier_obj()        
        if existing_snowflake_identfier_obj:
            raise HTTPException(status_code=400, detail="User has already snowflake identifier")
        
        snowflake_identfier_obj = SnowflakeIdentifier(
            user_id=self.user.user_id,
            account_identifier=config.account_identifier,
            client_id=config.client_id,
            client_secret=config.client_secret,
            token_endpoint=config.token_endpoint,
            authorization_endpoint=authorization_endpoint,
            warehouse=config.warehouse,
        )
        self.session.add(snowflake_identfier_obj)
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
        existing_snowflake_identfier_obj = self._get_snowflake_identifier_obj()        
        if not existing_snowflake_identfier_obj:
            raise HTTPException(status_code=400, detail="User does not have snowflake identifier object")
        return SnowflakeOauthMapper.map_to_chat_response(existing_snowflake_identfier_obj)


    def update_oauth_logic(self, config):
        existing_snowflake_identfier_obj = self._get_snowflake_identifier_obj()        
        if not existing_snowflake_identfier_obj:
            raise HTTPException(status_code=400, detail="User does not have snowflake identifier object")
        authorization_endpoint = config.token_endpoint.replace("token-request", "authorize")

        existing_snowflake_identfier_obj.account_identifier = config.account_identifier
        existing_snowflake_identfier_obj.client_id = config.client_id
        existing_snowflake_identfier_obj.client_secret = config.client_secret
        existing_snowflake_identfier_obj.token_endpoint = config.token_endpoint
        existing_snowflake_identfier_obj.authorization_endpoint = authorization_endpoint
        existing_snowflake_identfier_obj.warehouse = config.warehouse
        self.session.commit()
        params = {
            "response_type": "code",
            "client_id": config.client_id,
            "redirect_uri": REDIRECT_URI, 
            "account": config.account_identifier,
        }
        authorization_url = f"{authorization_endpoint}?{urlencode(params)}"

        return {"authorization_url": authorization_url}


    def _get_snowflake_identifier_obj(self):
        snowflake_identifier_obj = self.session.query(SnowflakeIdentifier).filter(
            SnowflakeIdentifier.user_id == self.user.user_id
        ).first()
        return snowflake_identifier_obj

    # Callback endpoint for OAuth flow
    async def oauth_callback_logic(self, code: str):
        if not code:
            raise HTTPException(status_code=400, detail="Authorization code not provided")
        try:
            token_response = await self.exchange_code_for_token(code)
            if 'access_token' not in token_response:
                raise HTTPException(status_code=400, detail="Access token not in response")
            self.update_token_info(token_response)
            return token_response
        except HTTPStatusError as http_err:
            print(f"Error in exchange_code_for_token:{http_err}")
            raise HTTPException(status_code=500, detail="Internal Server Error")
        except NetworkError as net_err:
            print(f"Request error occurred: {net_err}")
            raise HTTPException(status_code=500, detail="Network error during token exchange")
        except (ConnectTimeout, ReadTimeout) as timeout_err:
            print(f"Timeout error: {timeout_err}")
            raise HTTPException(status_code=500, detail="Timeout error during token exchange")
        except Exception as e:
            print(f"Unexpected error in exchange_code_for_token: {e}")
            raise HTTPException(status_code=500, detail="Internal Server Error")


    # Exchanges an authorization code for an access token
    async def exchange_code_for_token(self, code: str):
        snowflake_identifier_obj = self._get_snowflake_identifier_obj()
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    snowflake_identifier_obj.token_endpoint,
                    data={
                        "grant_type": "authorization_code",
                        "code": code,
                        "redirect_uri": snowflake_identifier_obj.redirect_uri,
                        "client_id": snowflake_identifier_obj.client_id,
                        "client_secret": snowflake_identifier_obj.client_secret
                    }
                )
            
            response.raise_for_status()
            return response.json()
        except HTTPStatusError as http_err:
            print(f"HTTP status error occurred: {http_err}")
            # Handle or re-raise HTTPStatusError as needed
        except NetworkError as net_err:
            print(f"Network error occurred: {net_err}")
            # Handle or re-raise NetworkError as needed
        except (ConnectTimeout, ReadTimeout) as timeout_err:
            print(f"Timeout error occurred: {timeout_err}")
            # Handle or re-raise timeout errors as needed
        except Exception as e:
            print(f"Unexpected error: {e}")
            # Handle or re-raise other unexpected exceptions

    # Method to update token information
    def update_token_info(self, token_data):
        self.token_info = {
            "access_token": token_data.get("access_token"),
            "refresh_token": token_data.get("refresh_token"),
            "expires_at": datetime.datetime.now() + datetime.timedelta(seconds=token_data.get("expires_in", 600))
        }

    # Check if the token is expired
    def is_token_expired(self):
        return datetime.datetime.now() >= self.token_info["expires_at"]

    # Get a valid access token, refresh if expired
    async def get_valid_access_token(self):
        if self.is_token_expired():
            await self.refresh_access_token_logic(self.token_info["refresh_token"])
        return self.token_info["access_token"]

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
                        "client_secret": snowflake_identifier_obj.client_secret
                    }
                )
                response.raise_for_status()
                new_token_data = response.json()
                self.update_token_info(new_token_data)
                return new_token_data
        except HTTPStatusError as http_err:
            print(f"HTTP status error during token refresh: {http_err}")
            # Handle or re-raise HTTPStatusError as needed
        except NetworkError as net_err:
            print(f"Network error during token refresh: {net_err}")
            # Handle or re-raise NetworkError as needed
        except (ConnectTimeout, ReadTimeout) as timeout_err:
            print(f"Timeout error during token refresh: {timeout_err}")
            # Handle or re-raise timeout errors as needed
        except Exception as e:
            print(f"Unexpected error during token refresh: {e}")
            # Handle or re-raise other unexpected exceptions


    # Creates a connection to Snowflake
    def create_snowflake_connection(self, oauth_token: str, snowflake_account: str):
        try: 
       
            ctx = snowflake.connector.connect(
                account=snowflake_account,
                authenticator='oauth',
                token=oauth_token
            )
            return ctx
        except DatabaseError as db_err:
            print(f"Database error occurred: {db_err}")
            # Handle specific DatabaseError here (e.g., log, raise a custom exception, etc.)
        except Exception as e:
            print(f"Unexpected error during Snowflake connection: {e}")
        

    # Endpoint to list data warehouses
    def list_data_warehouses_logic(self, token: str):
        snowflake_identifier_obj = self._get_snowflake_identifier_obj()
        
        # Check if the token is potentially expired
        if self.is_token_expired():
            raise ValueError("Token is expired or about to expire")

        try:
            ctx = self.create_snowflake_connection(token, snowflake_identifier_obj.account_identifier)
        except OperationalError:
            raise ConnectionError("Operational error when trying to connect to Snowflake")
        except InterfaceError:
            raise ConnectionError("Interface error when trying to connect to Snowflake")
        except DatabaseError:
            raise ConnectionError("General database error occurred during connection")

        cursor = ctx.cursor()
        try:
            cursor.execute("SHOW WAREHOUSES")
            warehouses = cursor.fetchall()
            # Assuming the first column contains the warehouse names
            warehouse_names = [wh[0] for wh in warehouses]  # Adjust the index if needed
            return {"data_warehouses": warehouse_names}
        except ProgrammingError:
            raise RuntimeError("SQL Programming error occurred while executing the query")
        except DatabaseError:
            raise RuntimeError("Database error occurred while executing the query")
        except Exception as e:
            print(f"Unexpected error during querying: {e}")
            raise RuntimeError("An unexpected error occurred while executing the query")
        finally:
            cursor.close()
            ctx.close()
            
    # Endpoint to select a data warehouse
    def select_warehouse_logic(self, token: str, warehouse_name: str):
        # Check if the token is valid
        if not self.is_token_valid(token):  # assuming is_token_valid is a method that checks token validity
            raise ValueError("Invalid or expired token provided")

        # Hypothetical method to check if warehouse exists
        if not self.warehouse_exists(warehouse_name):
            raise ValueError(f"Warehouse '{warehouse_name}' not found")

        try:
            # Hypothetical method to select the warehouse
            self.set_current_warehouse(token, warehouse_name)
        except PermissionError:
            raise PermissionError("Insufficient permissions to select the warehouse")
        except Exception as e:
            print(f"Unexpected error: {e}")
            raise RuntimeError("An unexpected error occurred while selecting the warehouse")

        return {"message": f"Data warehouse '{warehouse_name}' selected"}


    # Modified endpoint to list databases using the selected data warehouse
    def list_databases_logic(self, token: str):
        try:
            snowflake_identifier_obj = self._get_snowflake_identifier_obj()
            if not snowflake_identifier_obj.warehouse:
                raise HTTPException(status_code=400, detail="No data warehouse selected")

            conn = self.create_snowflake_connection(token, snowflake_identifier_obj.account_identifier)
            cursor = conn.cursor()

            try:
                cursor.execute(f"USE WAREHOUSE {snowflake_identifier_obj.warehouse}")
                cursor.execute("SHOW DATABASES")
                databases = cursor.fetchall()
                return {"databases": [db[1] for db in databases]}
            except ProgrammingError as prog_err:
                print(f"SQL Programming error: {prog_err}")
                raise HTTPException(status_code=400, detail="SQL programming error occurred")
            except DatabaseError as db_err:
                print(f"Database error: {db_err}")
                raise HTTPException(status_code=500, detail="Database error occurred")
            finally:
                cursor.close()
        except OperationalError as op_err:
            print(f"Operational error: {op_err}")
            raise HTTPException(status_code=500, detail="Operational error when trying to connect to Snowflake")
        except InterfaceError as if_err:
            print(f"Interface error: {if_err}")
            raise HTTPException(status_code=500, detail="Interface error when trying to connect to Snowflake")
        except DatabaseError as db_err:
            print(f"Database connection error: {db_err}")
            raise HTTPException(status_code=500, detail="Database connection error occurred")
        except Exception as e:
            print(f"Unexpected error: {e}")
            raise HTTPException(status_code=500, detail="Unexpected error occurred")
        finally:
            if 'conn' in locals() and conn is not None:
                conn.close()


    def get_schemas_logic(self, token: str, db_name: str):
        snowflake_identfier_obj = self._get_snowflake_identifier_obj()
        if not snowflake_identfier_obj.warehouse:
            raise HTTPException(status_code=400, detail="No data warehouse selected")

        ctx = self.create_snowflake_connection(token, snowflake_identfier_obj.account_identifier)
        cursor = ctx.cursor()
        try:
            cursor.execute(f"USE WAREHOUSE {snowflake_identfier_obj.warehouse}")
            cursor.execute(f"SHOW SCHEMAS IN DATABASE {db_name}")
            schemas = cursor.fetchall()
            return {"schemas": [schema[1] for schema in schemas]}
        finally:
            cursor.close()
            ctx.close()


    # Endpoint to select a schema and check separately for the existence of tables and views
    def select_schema_logic(self, token: str, db_name: str, schema_name: str):
        try:
            snowflake_identifier_obj = self._get_snowflake_identifier_obj()
            if not snowflake_identifier_obj.warehouse:
                raise HTTPException(status_code=400, detail="No data warehouse selected")

            conn = self.create_snowflake_connection(token, snowflake_identifier_obj.account_identifier)
            cursor = conn.cursor()

            try:
                cursor.execute(f"USE WAREHOUSE {snowflake_identifier_obj.warehouse}")
                cursor.execute(f"SHOW TABLES IN {db_name}.{schema_name}")
                tables_status = len(cursor.fetchall()) > 0

                cursor.execute(f"SHOW VIEWS IN {db_name}.{schema_name}")
                views_status = len(cursor.fetchall()) > 0

                return {
                    "message": f"Schema '{schema_name}' selected",
                    "tables": tables_status,
                    "views": views_status
                }
            except ProgrammingError as prog_err:
                print(f"SQL Programming error: {prog_err}")
                raise HTTPException(status_code=400, detail="SQL programming error occurred")
            except DatabaseError as db_err:
                print(f"Database error: {db_err}")
                raise HTTPException(status_code=500, detail="Database error occurred")
            finally:
                cursor.close()
        except OperationalError as op_err:
            print(f"Operational error: {op_err}")
            raise HTTPException(status_code=500, detail="Operational error when trying to connect to Snowflake")
        except InterfaceError as if_err:
            print(f"Interface error: {if_err}")
            raise HTTPException(status_code=500, detail="Interface error when trying to connect to Snowflake")
        except Exception as e:
            print(f"Unexpected error: {e}")
            raise HTTPException(status_code=500, detail="Unexpected error occurred")
        finally:
            if 'conn' in locals() and conn is not None:
                conn.close()
    # Endpoint to list tables of a specific schema in a Snowflake database
    def get_tables_logic(self, token: str, db_name: str, schema_name: str):
        try:
            snowflake_identifier_obj = self._get_snowflake_identifier_obj()
            if not snowflake_identifier_obj.warehouse:
                raise HTTPException(status_code=400, detail="No data warehouse selected")

            conn = self.create_snowflake_connection(token, snowflake_identifier_obj.account_identifier)
            cursor = conn.cursor()

            try:
                cursor.execute(f"USE WAREHOUSE {snowflake_identifier_obj.warehouse}")
                cursor.execute(f"SHOW TABLES IN {db_name}.{schema_name}")
                tables = cursor.fetchall()
                return {"tables": [table[1] for table in tables]}
            except ProgrammingError as prog_err:
                print(f"SQL Programming error: {prog_err}")
                raise HTTPException(status_code=400, detail="SQL programming error occurred")
            except DatabaseError as db_err:
                print(f"Database error: {db_err}")
                raise HTTPException(status_code=500, detail="Database error occurred")
            finally:
                cursor.close()
        except OperationalError as op_err:
            print(f"Operational error: {op_err}")
            raise HTTPException(status_code=500, detail="Operational error when trying to connect to Snowflake")
        except InterfaceError as if_err:
            print(f"Interface error: {if_err}")
            raise HTTPException(status_code=500, detail="Interface error when trying to connect to Snowflake")
        except DatabaseError as db_err:
            print(f"Database connection error: {db_err}")
            raise HTTPException(status_code=500, detail="Database connection error occurred")
        except Exception as e:
            print(f"Unexpected error: {e}")
            raise HTTPException(status_code=500, detail="Unexpected error occurred")
        finally:
            if 'conn' in locals() and conn is not None:
                conn.close()


    # Endpoint to list views of a specific schema in a Snowflake database

    def get_views_logic(self, token: str, db_name: str, schema_name: str):
        try:
            snowflake_identifier_obj = self._get_snowflake_identifier_obj()
            if not snowflake_identifier_obj.warehouse:
                raise HTTPException(status_code=400, detail="No data warehouse selected")

            conn = self.create_snowflake_connection(token, snowflake_identifier_obj.account_identifier)
            cursor = conn.cursor()

            try:
                cursor.execute(f"USE WAREHOUSE {snowflake_identifier_obj.warehouse}")
                cursor.execute(f"SHOW VIEWS IN {db_name}.{schema_name}")
                views = cursor.fetchall()
                return {"views": [view[1] for view in views]}
            except ProgrammingError as prog_err:
                print(f"SQL Programming error: {prog_err}")
                raise HTTPException(status_code=400, detail="SQL programming error occurred")
            except DatabaseError as db_err:
                print(f"Database error: {db_err}")
                raise HTTPException(status_code=500, detail="Database error occurred")
            finally:
                cursor.close()
        except OperationalError as op_err:
            print(f"Operational error: {op_err}")
            raise HTTPException(status_code=500, detail="Operational error when trying to connect to Snowflake")
        except InterfaceError as if_err:
            print(f"Interface error: {if_err}")
            raise HTTPException(status_code=500, detail="Interface error when trying to connect to Snowflake")
        except DatabaseError as db_err:
            print(f"Database connection error: {db_err}")
            raise HTTPException(status_code=500, detail="Database connection error occurred")
        except Exception as e:
            print(f"Unexpected error: {e}")
            raise HTTPException(status_code=500, detail="Unexpected error occurred")
        finally:
            if 'conn' in locals() and conn is not None:
                conn.close()

    # Endpoint to list columns of a specific table or view in a Snowflake database, including name and type

    def get_columns_logic(self, token: str, db_name: str, schema_name: str, table_or_view_name: str):
        try:
            snowflake_identifier_obj = self._get_snowflake_identifier_obj()
            if not snowflake_identifier_obj.warehouse:
                raise HTTPException(status_code=400, detail="No data warehouse selected")

            conn = self.create_snowflake_connection(token, snowflake_identifier_obj.account_identifier)
            cursor = conn.cursor()

            try:
                cursor.execute(f"USE WAREHOUSE {snowflake_identifier_obj.warehouse}")
                cursor.execute(f"DESCRIBE TABLE {db_name}.{schema_name}.{table_or_view_name}")
                columns = cursor.fetchall()
                # Format the columns data to include only name and type. Adjust indices based on Snowflake's response format
                columns_data = [{"name": col[0], "type": col[1]} for col in columns]
                return {"columns": columns_data}
            except ProgrammingError as prog_err:
                print(f"SQL Programming error: {prog_err}")
                raise HTTPException(status_code=400, detail="SQL programming error occurred")
            except DatabaseError as db_err:
                print(f"Database error: {db_err}")
                raise HTTPException(status_code=500, detail="Database error occurred")
            finally:
                cursor.close()
        except OperationalError as op_err:
            print(f"Operational error: {op_err}")
            raise HTTPException(status_code=500, detail="Operational error when trying to connect to Snowflake")
        except InterfaceError as if_err:
            print(f"Interface error: {if_err}")
            raise HTTPException(status_code=500, detail="Interface error when trying to connect to Snowflake")
        except DatabaseError as db_err:
            print(f"Database connection error: {db_err}")
            raise HTTPException(status_code=500, detail="Database connection error occurred")
        except Exception as e:
            print(f"Unexpected error: {e}")
            raise HTTPException(status_code=500, detail="Unexpected error occurred")
        finally:
            if 'conn' in locals() and conn is not None:
                conn.close()

    # Endpoint to preview data from a specific table or view in a Snowflake database
    def preview_data_logic(self, token: str, db_name: str, schema_name: str, table_or_view_name: str):
        try:
            snowflake_identifier_obj = self._get_snowflake_identifier_obj()
            if not snowflake_identifier_obj.warehouse:
                raise HTTPException(status_code=400, detail="No data warehouse selected")

            conn = self.create_snowflake_connection(token, snowflake_identifier_obj.account_identifier)
            cursor = conn.cursor()

            try:
                cursor.execute(f"USE WAREHOUSE {snowflake_identifier_obj.warehouse}")
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
            except ProgrammingError as prog_err:
                print(f"SQL Programming error: {prog_err}")
                raise HTTPException(status_code=400, detail="SQL programming error occurred")
            except DatabaseError as db_err:
                print(f"Database error: {db_err}")
                raise HTTPException(status_code=500, detail="Database error occurred")
            finally:
                cursor.close()
        except OperationalError as op_err:
            print(f"Operational error: {op_err}")
            raise HTTPException(status_code=500, detail="Operational error when trying to connect to Snowflake")
        except InterfaceError as if_err:
            print(f"Interface error: {if_err}")
            raise HTTPException(status_code=500, detail="Interface error when trying to connect to Snowflake")
        except DatabaseError as db_err:
            print(f"Database connection error: {db_err}")
            raise HTTPException(status_code=500, detail="Database connection error occurred")
        except Exception as e:
            print(f"Unexpected error: {e}")
            raise HTTPException(status_code=500, detail="Unexpected error occurred")
        finally:
            if 'conn' in locals() and conn is not None:
                conn.close()