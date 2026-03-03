FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY snmpserv.py .

RUN useradd -m appuser
USER appuser

ENV LISTEN_HOST=0.0.0.0
ENV LISTEN_PORT=1162
ENV V3_USERS="test:SHA:qwe12345:AES:qwe12345"
ENV DEBUG_SNMP=0

CMD ["python", "-u", "snmpserv.py"]
