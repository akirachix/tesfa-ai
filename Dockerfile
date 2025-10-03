FROM python:3.13-slim
WORKDIR /app

COPY tesfa_agent/requirements.txt .
RUN pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r tesfa_agent/requirements.txt

COPY . .

RUN adduser --disabled-password --gecos "" myuser \
    && chown -R myuser:myuser /app
USER myuser
ENV PATH="/home/myuser/.local/bin:$PATH"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
