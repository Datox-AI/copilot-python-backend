# from setuptools import setup, find_packages

# setup(name="Datox Copilot", version="1.0", packages=find_packages())
#!/usr/bin/env python
from setuptools import setup, find_packages

setup(
    name="Datox Copilot",
    version="1.0.0",
    description="Datox Copilot API",
    author="datox.ai",
    classifiers=["Programming Language :: Python :: 3 :: Only"],
    # py_modules=["tap_zerto"],
    install_requires=[
        "alembic==1.13.1",
        "azure-storage-blob==12.19.0",
        "fastapi==1.109.0",
        "fastapi-azure-auth==4.3.0",
        "langchain==0.1.3",
        "python-dotenv",
        "pydantic-settings==2.1.0",
        "pandas",
        "snowflake-connector-python==3.6.0",
        "snowflake-sqlalchemy==1.5.1",
        "SQLAlchemy==1.4.51",
        "tiktoken==0.5.2",
    ],
    packages=find_packages(),
)