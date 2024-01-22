# 
FROM python:3.11
# 
WORKDIR /code
# 
# COPY ./requirements.txt /code/requirements.txt
# 
COPY ./setup.py /code/setup.py

RUN pip install --no-cache-dir . 

# 
COPY ./app /code/app
COPY ./.env /code/.env

COPY ./migrations /code/migrations
COPY ./alembic.ini /code/alembic.ini
COPY ./SSL /code/SSL

# 

# 
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80", "--ssl-keyfile=SSL/localhost.key", "--ssl-certfile=SSL/fullchain.pem"]