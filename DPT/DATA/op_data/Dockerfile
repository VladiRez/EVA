FROM 192.168.56.104:5000/base_module
WORKDIR /app
COPY op_data.py op_data.py
RUN ["pip", "install", "pymongo"]
CMD ["python", "op_data.py"]