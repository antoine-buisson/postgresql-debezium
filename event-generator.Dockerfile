FROM python:3.11.6-slim

COPY event-generator event-generator

RUN pip install --no-cache-dir -r /event-generator/requirements.txt

CMD ["python", "/event-generator/main.py"]
