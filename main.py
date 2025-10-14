import os
from pathlib import Path
from dotenv import load_dotenv


env_path = Path(".") / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    agent_env = Path("tesfa_agent") / ".env"
    if agent_env.exists():
        load_dotenv(agent_env)

from fastapi import FastAPI
from google.adk.cli.fast_api import get_fast_api_app

AGENT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tesfa_agent")
session_service_uri = "sqlite:///./sessions.db"
ALLOWED_ORIGINS = ["*"]
SERVE_WEB_INTERFACE = True

try:
    from tesfa_agent import root_agent
    print(f"Agent '{root_agent.name}' loaded successfully at startup.")
except Exception as e:
    print(f"CRITICAL: Failed to load agent: {e}")
    raise

app: FastAPI = get_fast_api_app(
    agents_dir=AGENT_DIR,
    session_service_uri=session_service_uri,
    allow_origins=ALLOWED_ORIGINS,
    web=SERVE_WEB_INTERFACE,
)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    print(f"Starting server on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)