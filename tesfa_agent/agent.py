import os
from google.adk.agents import LlmAgent
from .tools import retrieve_context, predict_health_risk
from .prompt import instruction_text

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    raise EnvironmentError(
        "GOOGLE_API_KEY is not set. "
        "This is required for the agent to function."
    )

if not GOOGLE_API_KEY.startswith("AIza"):
    raise ValueError("GOOGLE_API_KEY appears invalid.")

root_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="tesfa_agent",
    description="Predicts long-term health risks in post-conflict regions using RAG and local BioGPT.",
    instruction=instruction_text,
    tools=[retrieve_context, predict_health_risk]
)