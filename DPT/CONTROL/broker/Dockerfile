FROM python:alpine
WORKDIR /app
RUN ["pip", "install", "pyzmq"]
COPY broker.py broker.py
CMD ["python", "broker.py"]
