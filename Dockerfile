# 
FROM python:3.11
# 
WORKDIR /code
# 
# COPY ./requirements.txt /code/requirements.txt
# 
COPY ./setup.py /code/setup.py

# 
COPY ./app /code/app
COPY ./.env /code/.env
COPY ./migrations /code/migrations
COPY ./alembic.ini /code/alembic.ini
COPY ./SSL /code/SSL

RUN python setup.py install 

# 
# RUN alembic -n admin upgrade head
# RUN alembic -n main upgrade head

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]
