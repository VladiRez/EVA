FROM 192.168.56.104:5000/base_module
COPY requirements.txt /app/requirements.txt
RUN ["pip", "install", "-r", "/app/requirements.txt"]
COPY process_ui /app/process_ui
WORKDIR /app/process_ui
ENV MODULE_NAME process_ui
CMD ["gunicorn", "-b", ":8000", "process_ui.wsgi"]



