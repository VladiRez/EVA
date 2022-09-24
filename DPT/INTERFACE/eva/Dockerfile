ARG REGISTRY

FROM $REGISTRY/base_module
WORKDIR /app
COPY requirements.txt requirements.txt
RUN ["pip", "install", "-r", "requirements.txt"]
COPY eva.py eva.py
ENV MODULE_NAME eva-interface
ENV OP_DATA_SERVER_COUNT 1
CMD ["python", "eva.py"]