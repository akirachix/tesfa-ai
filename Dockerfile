FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .

RUN pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p /app/agents && mv /app/tesfa_agent /app/agents/ \
    && adduser --disabled-password --gecos "" myuser \
    && chown -R myuser:myuser /app

USER myuser

ENV PATH="/home/myuser/.local/bin:$PATH"

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
