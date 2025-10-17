FROM python:3.11-slim
WORKDIR /app

COPY requirements.txt .

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential git curl libsndfile1 ffmpeg \
  && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip setuptools wheel \
 && pip install --no-cache-dir torch==2.2.0+cpu -f https://download.pytorch.org/whl/cpu/torch_stable.html \
 && pip install --no-cache-dir -r requirements.txt

COPY main.py .
COPY tesfa_agent/ ./tesfa_agent/

RUN adduser --disabled-password --gecos "" myuser \
    && chown -R myuser:myuser /app
USER myuser
ENV PATH="/home/myuser/.local/bin:$PATH"

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]