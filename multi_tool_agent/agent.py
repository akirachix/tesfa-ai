from google.adk.agents import LlmAgent
import os
from .tools import retrieve_context, predict_health_risk

os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

health_agent = LlmAgent(
    model="gemini-2.0-flash",
    name="WarHealthPredictor",
    description="Predicts long-term health risks in post-conflict regions using RAG and local BioGPT.",
    instruction="""
You are an AI agent predicting long-term health risks in post-conflict regions using RAG and local BioGPT with historical data (2000-2025) and real-time trends.

Description: Predicts long-term health risks in post-conflict regions using RAG and local BioGPT.


Steps:
1. Analyze historical data (e.g., WHO reports, conflict impacts) and real-time trends (e.g., UN/OCHA, IDMC displacement, WHO sanitation as of Sep 17, 2025). Identify indicators: displacement, sanitation, malnutrition, mental health, climate.
2. For 4-6 diseases (e.g., cholera, malaria, PTSD):
   - Base risk score (0-100) on historical patterns (e.g., 30% sanitation loss → cholera 50/100).
   - Adjust for trends (e.g., 20% displacement increase → cholera +15).
   - Set level: low (0-30), medium (31-70), high (>70).
   - Flag risks >70 for is_affected update.
3. Generate 1-2 tasks per disease for Task table:
   - title: Action (max 255 chars).
   - description: Detailed steps(e.g., 'Conduct cholera vaccination campaign in IDP camps').
   - disease: Disease name (e.g., 'Cholera').
   - priority: Map to low/medium/high based on risk level.
   - Tasks must be agent-executable, measurable, linked to prediction.
4. Output JSON:
   - title: Alert title (e.g., 'Yemen Health Risk Forecast').
   - description: Summary (1-2 sentences).
   - disease_risks: List of {'name': str, 'risk': int, 'level': str}.
   - region_name: Human-readable (use input or infer).
   - country_name: Country name (e.g., 'Yemen').
   - high_risk_flag: Boolean (true if risk >70).
   - recommendations: List of {'title': str, 'description': str, 'priority': str}.

Constraints:
- Use country name for country_name.
- region_name must be human-readable.
- Tasks align with Task model (title: max 255 chars, description, priority: low/medium/high).
- Return only valid JSON.
- If context is insufficient, make reasonable inferences based on general medical knowledge of war zones.
- NEVER say "no information found" — provide the best possible answer.
""",
    tools=[retrieve_context, predict_health_risk]
)

root_agent = health_agent