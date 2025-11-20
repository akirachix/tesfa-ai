"""
Tesfa AI Agent - Main Application Entry Point

This module initializes and configures the FastAPI application using Google's
Agent Development Kit (ADK). It serves as the entry point for the health risk
prediction system for conflict-affected regions.

Key Features:
- FastAPI server with Google ADK integration
- Session management using SQLite
- CORS configuration for web interface access
- Health check for PyTorch/CUDA availability
"""

import os
from fastapi import FastAPI
import uvicorn
from google.adk.cli.fast_api import get_fast_api_app

# Get port from environment or default to 8080 (required for Cloud Run)
PORT = os.environ.get("PORT", "8080")
print(f"STARTUP: environment PORT={PORT}")

# Verify PyTorch installation and GPU availability
# BioGPT will use GPU if available for faster inference
try:
    import torch
    print("STARTUP: torch import ok:", getattr(torch, "__version__", "unknown"), "cuda_available=", torch.cuda.is_available())
except Exception as e:
    print("STARTUP: torch import failed:", repr(e))

# Configure agent directory and session storage
AGENT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tesfa_agent")
session_service_uri = "sqlite:///./sessions.db"  # Local SQLite for session persistence

# CORS settings - allows web interface from any origin
ALLOWED_ORIGINS = ["*"]  # In production, restrict to specific domains

# Enable built-in web chat interface
SERVE_WEB_INTERFACE = True

# Initialize FastAPI application with Google ADK
# This creates the agent server with:
# - Automatic API endpoint generation (/api/chat)
# - Web interface at root URL (/)
# - Session management and conversation history
# - Agent discovery from AGENT_DIR
app: FastAPI = get_fast_api_app(
    agents_dir=AGENT_DIR,
    session_service_uri=session_service_uri,
    allow_origins=ALLOWED_ORIGINS,
    web=SERVE_WEB_INTERFACE,
)

if __name__ == "__main__":
    # Start uvicorn server
    # Binds to 0.0.0.0 to accept connections from any IP (required for containers)
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)