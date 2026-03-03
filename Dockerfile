FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY snmpserv.py .

RUN useradd -m appuser
USER appuser

ENV LISTEN_HOST=0.0.0.0
ENV LISTEN_PORT=162

CMD ["python", "snmpserv.py"]
