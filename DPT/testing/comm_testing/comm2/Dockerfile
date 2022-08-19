FROM base_module
ENV ZMQ_PORT=5554
WORKDIR /app
RUN ["pip", "install", "pyzmq"]
COPY comm2.py comm2.py
CMD ["python", "comm2.py"]