from google.adk.agents import LlmAgent
import os
from .tools import retrieve_context, predict_health_risk
from dotenv import load_dotenv
from .prompt import instruction_text


load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY

health_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="tesfa_agent",
    description="Predicts long-term health risks in post-conflict regions using RAG and local BioGPT.",
    instruction=instruction_text,
   tools=[retrieve_context, predict_health_risk]
)

root_agent = health_agent

