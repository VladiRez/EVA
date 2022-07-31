FROM python:alpine
WORKDIR /app
COPY base_module base_module
RUN ["pip", "install", "-r", "base_module/requirements.txt"]
RUN ["pip", "install", "./base_module"]
RUN ["rm", "-R", "base_module"]
