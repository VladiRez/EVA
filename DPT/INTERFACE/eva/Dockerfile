FROM 192.168.56.104:5000/base_module
WORKDIR /app
COPY requirements.txt requirements.txt
RUN ["pip", "install", "-r", "requirements.txt"]
COPY eva.py eva.py
CMD ["python", "eva.py"]