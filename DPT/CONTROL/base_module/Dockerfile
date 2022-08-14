FROM python:alpine
WORKDIR /app
COPY base_module/requirements.txt requirements.txt
RUN ["pip", "install", "-r", "requirements.txt"]
COPY base_module base_module
RUN ["pip", "install", "./base_module"]
RUN ["rm", "-R", "base_module"]
ENV ZMQ_PORT 5554
