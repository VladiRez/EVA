ARG REGISTRY

FROM $REGISTRY/base_module
WORKDIR /app
RUN ["pip", "install", "pymongo"]
COPY op_data.py op_data.py
ENV MODULE_NAME op-data-interface
CMD ["python", "op_data.py"]