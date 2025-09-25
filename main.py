import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import uvicorn
from google.adk.cli.fast_api import get_fast_api_app
from google.adk.sessions import DatabaseSessionService
import urllib.parse
import json
from typing import Any, Dict

AGENT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tesfa_agent")
session_service_uri = "sqlite:///./sessions.db"
ALLOWED_ORIGINS = ["*"]
SERVE_WEB_INTERFACE = True

# Create the base app first
app: FastAPI = get_fast_api_app(
    agents_dir=AGENT_DIR,
    session_service_uri=session_service_uri,
    allow_origins=ALLOWED_ORIGINS,
    web=SERVE_WEB_INTERFACE,
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Custom validation error handler to provide better error messages
    and handle form-encoded data that should be JSON.
    """
    # Check if this is the specific error about expecting a dictionary
    for error in exc.errors():
        if (error.get("type") == "model_attributes_type" and 
            error.get("msg") == "Input should be a valid dictionary or object to extract fields from"):
            
            # Try to parse the input as form data
            raw_input = error.get("input", "")
            if isinstance(raw_input, str) and "=" in raw_input:
                try:
                    # Parse URL-encoded data
                    parsed_data = urllib.parse.parse_qs(raw_input)
                    
                    # Convert to flat dictionary (take first value for each key)
                    flat_data: Dict[str, Any] = {}
                    for key, values in parsed_data.items():
                        flat_data[key] = values[0] if values else ""
                    
                    # Return a helpful error message
                    return JSONResponse(
                        status_code=400,
                        content={
                            "error": "Invalid request format",
                            "message": "Request body should be JSON format, not form-encoded data.",
                            "received_form_data": flat_data,
                            "expected_format": "Send JSON in request body, e.g., {\"query\": \"your question here\"}",
                            "curl_example": "curl -X POST -H 'Content-Type: application/json' -d '{\"query\":\"your question\"}' /endpoint"
                        }
                    )
                except Exception:
                    pass
    
    # Fall back to default error format
    return JSONResponse(
        status_code=422,
        content={
            "detail": exc.errors(),
            "message": "Request validation failed. Ensure you're sending JSON format with correct field names."
        }
    )

if __name__ == "__main__":
   
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))