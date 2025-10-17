import os
from fastapi import FastAPI
import uvicorn
from google.adk.cli.fast_api import get_fast_api_app

PORT = os.environ.get("PORT", "8080")
print(f"STARTUP: environment PORT={PORT}")
try:
    import torch
    print("STARTUP: torch import ok:", getattr(torch, "__version__", "unknown"), "cuda_available=", torch.cuda.is_available())
except Exception as e:
    print("STARTUP: torch import failed:", repr(e))

AGENT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tesfa_agent")
session_service_uri = "sqlite:///./sessions.db"
ALLOWED_ORIGINS = ["*"]
SERVE_WEB_INTERFACE = True

app: FastAPI = get_fast_api_app(
    agents_dir=AGENT_DIR,
    session_service_uri=session_service_uri,
    allow_origins=ALLOWED_ORIGINS,
    web=SERVE_WEB_INTERFACE,
)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)