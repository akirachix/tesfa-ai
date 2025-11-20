"""
Tesfa AI Tools - Core Functionality

This module implements the two main tools used by the agent:
1. retrieve_context: Hybrid RAG system (Supabase + web search)
2. predict_health_risk: Medical AI analysis (BioGPT + Gemini)

The tools use global caching to avoid reloading models on each request,
significantly improving performance.
"""

import os
import re
import json
import torch
import psycopg2
import time
from typing import List, Dict, Optional
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModelForCausalLM
from duckduckgo_search import DDGS
import google.generativeai as genai


# Global variables for caching connections and models
# These are initialized once and reused across requests
_conn = None  # Supabase PostgreSQL connection
_cur = None  # Database cursor
_embedding_model = None  # SentenceTransformer for text embeddings
_bio_gpt_model = None  # BioGPT model
_bio_gpt_tokenizer = None  # BioGPT tokenizer


def get_supabase_client():
    """
    Initialize and return Supabase PostgreSQL connection with embedding model.
    
    Uses connection pooling - establishes connection once and reuses it.
    Also loads the SentenceTransformer model for generating query embeddings.
    
    Returns:
        tuple: (cursor, embedding_model) for database queries and text encoding
    """
    global _conn, _cur, _embedding_model
    if _conn is None:
        print("Connecting to Supabase Postgres...")
        _conn = psycopg2.connect(
            host=os.getenv("SUPABASE_HOST"),
            dbname=os.getenv("SUPABASE_DB"),
            user=os.getenv("SUPABASE_USER"),
            password=os.getenv("SUPABASE_PASSWORD"),
            port="5432",
            sslmode="require"  # Secure connection required for cloud database
        )
        _cur = _conn.cursor()
        print("[INFO] Connected to Supabase Postgres")
    if _embedding_model is None:
        # Load lightweight embedding model (384 dimensions)
        # This model converts text to vectors for similarity search
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _cur, _embedding_model
def get_bio_gpt():
    """
    Initialize and return BioGPT model and tokenizer.
    
    BioGPT is a medical language model pretrained on PubMed abstracts.
    It provides domain-specific medical knowledge for health risk analysis.
    
    First call downloads ~1.6GB model from Hugging Face Hub.
    Subsequent calls load from cache (~/.cache/huggingface).
    
    Returns:
        tuple: (model, tokenizer) for text generation
    """
    global _bio_gpt_model, _bio_gpt_tokenizer
    if _bio_gpt_model is None:
        print("Loading BioGPT model (this may take 1-2 minutes)...")
        _bio_gpt_tokenizer = AutoTokenizer.from_pretrained("microsoft/BioGPT")
        _bio_gpt_model = AutoModelForCausalLM.from_pretrained("microsoft/BioGPT")
        
        # Move to GPU if available for faster inference
        if torch.cuda.is_available():
            _bio_gpt_model = _bio_gpt_model.to("cuda")
            print("BioGPT loaded on GPU.")
        else:
            print("BioGPT loaded on CPU.")
    return _bio_gpt_model, _bio_gpt_tokenizer
def retrieve_context(query: str) -> List[Dict]:
    """
    Hybrid RAG retrieval system combining vector database and web search.
    
    This is Tool #1 used by the agent to gather relevant information before
    making health risk predictions.
    
    Retrieval Strategy:
    1. Primary: Query Supabase pgvector database for stored conflict health data
    2. Fallback: If Supabase results are weak, search the web via DuckDuckGo
    
    Args:
        query: User's question or search query
        
    Returns:
        List of context dictionaries with keys:
        - content: Text content of the document
        - source: Where the data came from (file name or URL)
        - region: Geographic area (e.g., "Aleppo Governorate")
        - type: "supabase" or "web"
    
    Example:
        contexts = retrieve_context("What are cholera risks in Yemen?")
        # Returns: [
        #   {"content": "...", "source": "yemen_health_2024.pdf", 
        #    "region": "Sana'a", "type": "supabase"},
        #   ...
        # ]
    """
    contexts = []
    cur, model = get_supabase_client()
    
    # Step 1: Convert query to embedding vector
    query_embedding = model.encode([query])[0].tolist()
    top_k = 3  # Retrieve top 3 most similar documents
    region = None  # Could be extracted from query if needed
   
    # Step 2: Query Supabase using vector similarity search
    # The <-> operator finds nearest neighbors in vector space
    cur.execute(
        """
        SELECT id, content, metadata
        FROM embeddings
        ORDER BY embedding <-> %s::vector
        LIMIT %s;
        """,
        (query_embedding, top_k)
    )
    results = cur.fetchall()
    
    # Parse Supabase results
    for row in results:
        id_, content, metadata = row
        contexts.append({
            "content": content,
            "source": metadata.get("source_file", "supabase_db"),
            "region": metadata.get("region", "unknown"),
            "type": "supabase"
        })
    
    supabase_results_count = len(results)
    
    # Step 3: Determine if we need web search fallback
    # Weak results = less than 2 docs OR all docs are very short
    supabase_has_good_results = (
        supabase_results_count >= 2
        and any(len(doc["content"]) > 200 for doc in contexts)
    )
   
    # Step 4: Fallback to web search if needed
    if not supabase_has_good_results:
        print(f"[INFO] Supabase results weak — searching web for: '{query}'")
        try:
            with DDGS() as ddgs:
                ddgs_results = ddgs.text(query, max_results=top_k)
                for r in ddgs_results:
                    contexts.append({
                        "content": r.get("body", "")[:2000],  # Limit to 2000 chars
                        "source": r.get("href", "web_search"),
                        "region": region or "global",
                        "type": "web"
                    })
                    time.sleep(0.5)  # Rate limiting to avoid being blocked
        except Exception as e:
            print(f"[ERROR] Web search failed: {e}")
    
    print(f"[INFO] Retrieved {len(contexts)} contexts "
          f"({supabase_results_count} from Supabase, {len(contexts)-supabase_results_count} from web)")
    
    return contexts[:top_k]  # Return top 3 total contexts
def predict_health_risk(context: str, question: str) -> Dict:
    """
    Predict health risks using BioGPT + Gemini two-stage pipeline.
    
    This is Tool #2 used by the agent to generate structured health risk
    assessments based on retrieved context.
    
    Two-Stage Process:
    1. BioGPT: Generate medical reasoning and analysis (unstructured text)
    2. Gemini: Convert BioGPT output to structured JSON format
    
    Args:
        context: Retrieved background information (from retrieve_context)
        question: User's specific question about health risks
        
    Returns:
        Dictionary with:
        - risk_level: "Low", "Medium", "High", or "Critical"
        - diseases: List of disease names (e.g., ["Cholera", "Malaria"])
        - reason: Brief explanation of the risk
        - recommendations: List of actionable steps for NGOs
        
    Example:
        result = predict_health_risk(
            context="Yemen has limited water access...",
            question="What are the health risks?"
        )
        # Returns: {
        #   "risk_level": "High",
        #   "diseases": ["Cholera", "Malnutrition"],
        #   "reason": "Poor water infrastructure increases waterborne disease risk",
        #   "recommendations": ["Deploy mobile health clinics", "Establish WASH programs"]
        # }
    
    Fallback Behavior:
        If any step fails (model loading, API calls, JSON parsing), returns
        worst-case scenario to ensure humanitarian organizations err on the
        side of caution.
    """
    try:
        # ========== STAGE 1: BioGPT Medical Analysis ==========
        model, tokenizer = get_bio_gpt()
        
        # Construct prompt for medical AI
        # Instructs BioGPT to make inferences even with incomplete data
        prompt = f"""
You are a medical expert. Answer the question using the context below.
If the context is incomplete, make reasonable inferences based on general medical knowledge of war zones.
Do NOT say "no information found" — provide the best possible answer.
Question: {question}
Context (first 800 chars): {context[:800]}
Answer in 2-3 sentences.
"""
        # Tokenize and prepare for generation
        inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)
        if torch.cuda.is_available():
            inputs = {k: v.to("cuda") for k, v in inputs.items()}
        
        # Generate medical analysis using BioGPT
        outputs = model.generate(
            **inputs,
            max_new_tokens=200,  # Limit output length
            num_return_sequences=1,
            temperature=0.7,  # Some randomness for natural language
            do_sample=True,  # Enable sampling (vs greedy)
            pad_token_id=tokenizer.eos_token_id
        )
        bio_gpt_answer = tokenizer.decode(outputs[0], skip_special_tokens=True)
        print(f" BioGPT Raw Answer:\n{bio_gpt_answer}\n{'='*50}")
        
        # ========== STAGE 2: Gemini JSON Formatting ==========
        # Convert unstructured medical text to structured JSON
        gemini_prompt = f"""
You are a data formatter. Convert the following medical answer into JSON with keys: "risk_level", "diseases", "reason", "recommendations".
Medical Answer:
{bio_gpt_answer}
Rules:
- risk_level: "Low", "Medium", "High", or "Critical" — based on severity
- diseases: list of disease names mentioned or implied
- reason: 1-sentence summary of cause
- recommendations: 2-3 actionable steps for NGOs
- If diseases are not listed, infer from context
- NEVER return empty lists — make reasonable assumptions
"""
        
        # Call Gemini API
        genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
        gemini_model = genai.GenerativeModel('gemini-2.5-flash')
        gemini_response = gemini_model.generate_content(gemini_prompt)
        gemini_text = gemini_response.text.strip()
        print(f"Gemini Formatted Output:\n{gemini_text}\n{'='*50}")
        
        # ========== STAGE 3: JSON Extraction and Validation ==========
        # Extract JSON from Gemini's response (may include markdown)
        json_match = re.search(r'\{.*\}', gemini_text, re.DOTALL)
        if not json_match:
            raise ValueError("Gemini did not return JSON")
        
        json_str = json_match.group(0)
        # Clean up common JSON formatting issues
        json_str = json_str.replace("'", '"')  # Single quotes to double quotes
        json_str = re.sub(r',\s*([\}\]])', r'\1', json_str)  # Remove trailing commas
        
        parsed = json.loads(json_str)
        
        # Create output with defaults (defensive programming)
        output = {
            "risk_level": "Unknown",
            "diseases": ["General morbidity"],
            "reason": "Post-conflict health risks",
            "recommendations": ["Conduct health assessment", "Strengthen surveillance"]
        }
        
        # Map Gemini's output keys to expected keys (flexible key matching)
        key_mapping = {
            "risk_level": ["risk_level"],
            "diseases": ["diseases"],
            "reason": ["reason"],
            "recommendations": ["recommendations"]
        }
        for out_key, possible_keys in key_mapping.items():
            for p_key in possible_keys:
                if p_key in parsed:
                    output[out_key] = parsed[p_key]
                    break
        
        # Ensure lists are actually lists (type safety)
        if not isinstance(output["diseases"], list):
            output["diseases"] = [str(output["diseases"])]
        if not isinstance(output["recommendations"], list):
            output["recommendations"] = [str(output["recommendations"])]
        
        return output
        
    except Exception as e:
        # ========== FALLBACK: Worst-Case Scenario ==========
        # If anything fails, assume high risk to ensure safety
        print(f"Final Error: {e}")
        return {
            "risk_level": "High",
            "diseases": ["Unknown risks"],
            "reason": "Data retrieval failed — assume worst-case scenario",
            "recommendations": ["Deploy emergency medical teams", "Initiate rapid assessment"]
        }