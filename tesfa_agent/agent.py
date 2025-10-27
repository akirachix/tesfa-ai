import os
from .tools import retrieve_context, predict_health_risk
from .prompt import instruction_text
from google.adk.agents import LlmAgent

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if GOOGLE_API_KEY:
    os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY
else:
  
    print("[WARNING] GOOGLE_API_KEY is not set. Some features (Gemini calls) will fail at runtime.")

health_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="TesfaAIAgent",
    description="Predicts long-term health risks in post-conflict regions using RAG and local BioGPT.",
    instruction=instruction_text,
    tools=[retrieve_context, predict_health_risk]
)

root_agent = health_agent