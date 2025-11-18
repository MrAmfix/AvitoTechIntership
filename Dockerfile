FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y libpq-dev gcc netcat-traditional && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

RUN chmod +x ./entrypoint.sh
EXPOSE 8080

CMD ["./entrypoint.sh"]