FROM base_module
ENV ZMQ_PORT=5554
WORKDIR /app
RUN ["pip", "install", "pyzmq"]
COPY comm1.py comm1.py
CMD ["python", "comm1.py"]