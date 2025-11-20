"""
Tesfa AI Agent Configuration

This module defines the LLM agent that powers the health risk prediction system.
It combines Google's Gemini model with custom tools for RAG retrieval and
medical AI analysis.

Components:
- LlmAgent: Google ADK agent with Gemini 2.5 Flash
- Custom Tools: retrieve_context() and predict_health_risk()
- System Instructions: Behavior rules from prompt.py
"""

import os
from .tools import retrieve_context, predict_health_risk
from .prompt import instruction_text
from google.adk.agents import LlmAgent

# Load Google API key from environment
# Required for Gemini API calls - fail early if missing
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if GOOGLE_API_KEY:
    os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY
else:
    # Warning only - allows container to start, but Gemini calls will fail
    print("[WARNING] GOOGLE_API_KEY is not set. Some features (Gemini calls) will fail at runtime.")

# Create the health risk prediction agent
# - Model: Gemini 2.5 Flash (fast, cost-effective, good at JSON)
# - Tools: Custom functions for data retrieval and risk prediction
# - Instruction: System prompt defining behavior and output format
health_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="TesfaAIAgent",
    description="Predicts long-term health risks in post-conflict regions using RAG and local BioGPT.",
    instruction=instruction_text,  # From prompt.py - defines agent behavior
    tools=[retrieve_context, predict_health_risk]  # From tools.py - custom functions
)

# Export as root_agent (required by Google ADK)
root_agent = health_agent