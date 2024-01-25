# FastAPI Project README

## Overview

This repository contains a FastAPI application structured using a 3-tier architecture. It includes models for database entities, schemas for request and response data transfer objects (DTOs), services for business logic, and routers that function as controllers. The project is designed to work with two PostgreSQL databases and integrates Azure Active Directory (AAD) for authentication.


## Architecture

- **Models**: Representations of database entities.
- **Schemas**: DTOs for handling requests and responses.
- **Routers**: Act as controllers to route and handle API requests.
- **Enums**: A folder containing global enumerations used throughout the application.
- **Services**: This folder contains the business logic of the application. Implementing a mini CQRS pattern, the `services` folder is organized with separate files for each functionality. For instance, chat-related functionalities are split into `create_chat.py`, `delete_chat.py`, `get_chat.py`, etc.


## Databases
The project uses two PostgreSQL databases. Specific models (tables) are assigned to each database using `__table_args__` in their class definitions. For example, the `File` table belonging to the 'main' database is defined as follows:

```python
class File(BaseDelete):
    __table_args__ = ({ 'info': { 'dbname': 'main' }})
    __tablename__ = 'files'

    fileName = Column(String, nullable=False)
    blobName = Column(String, nullable=False)
``` 
- **Note**: These databases need to be created manually before running migrations.

## Authentication
- Authentication is managed through Azure Active Directory (AAD).

## Configuration
- All sensitive configurations like connection strings and app keys are stored in a `.env` file.

## Migrations
Migrations are managed using Alembic. Since the project uses two databases (main and admin), migrations should be specified for each database.

### Creating Migrations
Migrations are managed using Alembic. To ensure that Alembic recognizes all the tables for each database, import statements are required in the env.py file within the migration folder:

```python
from app.models.maindb import *
from app.models.admindb import *
```

When adding a new model, it should also be imported into its respective __init__.py file to be recognized by Alembic.

### Creating Migrations
To create a new migration for the main database:

```bash
alembic -n main revision --autogenerate -m "Added group admin"
```

### Applying Migrations
To apply migrations to the main database:

```bash
alembic -n main upgrade head
```

## Running the Application
Since AAD requires a secure redirect URI, the server should be run with a local SSL key.

### Command to Run the Server

```bash
uvicorn app.main:app --reload --ssl-keyfile=SSL/localhost-key.pem --ssl-certfile=SSL/localhost.pem --port 7202
```

**Important**: The auth redirect is configured for port 7202, so this port should be used for local development.

## Getting Started
1. **Set Up Databases**: Manually create the two PostgreSQL databases.
2. **Configure Environment**: Set up the `.env` file with the necessary configurations.
3. **Install Dependencies**: Run `pip install -r requirements.txt` to install the required packages.
4. **Run Migrations**: Apply migrations to both databases using the Alembic commands provided above.
5. **Start the Server**: Use the provided command to run the FastAPI server.





