FROM 192.168.56.104:base_module
WORKDIR /app
COPY dockertest.py dockertest.py
ENV BROKER_PORT 5554
ENV BROKER_NAME DPT_broker
CMD ["python", "dockertest.py"]
