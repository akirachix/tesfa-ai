import os
from fastapi import FastAPI
import uvicorn
from google.adk.cli.fast_api import get_fast_api_app
from google.adk.sessions import DatabaseSessionService


AGENT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tesfa_agent")
ALLOWED_ORIGINS = ["*"]
SERVE_WEB_INTERFACE = True


app: FastAPI = get_fast_api_app(
    agents_dir=AGENT_DIR,
    allow_origins=ALLOWED_ORIGINS,
    web=SERVE_WEB_INTERFACE,
)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
