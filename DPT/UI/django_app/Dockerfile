ARG REGISTRY

FROM $REGISTRY/base_module
COPY requirements.txt /app/requirements.txt
RUN ["pip", "install", "-r", "/app/requirements.txt"]
COPY process_ui /app/process_ui
WORKDIR /app/process_ui
ENV MODULE_NAME process_ui
ENV OP_DATA_SERVER_COUNT 1
ENV EVA_INTERFACE_SERVER_COUNT 1
CMD ["gunicorn", "-b", ":8000", "process_ui.wsgi"]



