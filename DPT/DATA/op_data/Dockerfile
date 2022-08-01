FROM 192.168.56.104:5000/base_module
WORKDIR /app
RUN ["pip", "install", "pymongo"]
COPY op_data.py op_data.py
CMD ["python", "op_data.py"]