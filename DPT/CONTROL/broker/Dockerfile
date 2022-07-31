FROM python:alpine
WORKDIR /app
COPY broker.py broker.py
RUN ["pip", "install", "pyzmq"]
CMD ["python", "broker.py"]
