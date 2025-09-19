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


_conn = None
_cur = None
_embedding_model = None
_bio_gpt_model = None
_bio_gpt_tokenizer = None

def get_supabase_client():
    global _conn, _cur, _embedding_model
    if _conn is None:
        print("Connecting to Supabase Postgres...")
        _conn = psycopg2.connect(
            host=os.getenv("SUPABASE_HOST"),
            dbname=os.getenv("SUPABASE_DB"),
            user=os.getenv("SUPABASE_USER"),
            password=os.getenv("SUPABASE_PASSWORD"),
            port="5432",
            sslmode="require"
        )
        _cur = _conn.cursor()
        print("[INFO] Connected to Supabase Postgres")
    if _embedding_model is None:

        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _cur, _embedding_model
def get_bio_gpt():
    global _bio_gpt_model, _bio_gpt_tokenizer
    if _bio_gpt_model is None:
        print("Loading BioGPT model (this may take 1-2 minutes)...")
        _bio_gpt_tokenizer = AutoTokenizer.from_pretrained("microsoft/BioGPT")
        _bio_gpt_model = AutoModelForCausalLM.from_pretrained("microsoft/BioGPT")
        if torch.cuda.is_available():
            _bio_gpt_model = _bio_gpt_model.to("cuda")
            print("BioGPT loaded on GPU.")
        else:
            print("BioGPT loaded on CPU.")
    return _bio_gpt_model, _bio_gpt_tokenizer
def retrieve_context(query: str, region: Optional[str] = None, top_k: int = 3) -> List[Dict]:
    """
    Hybrid retriever: queries Supabase pgvector first,
    falls back to web search if results are weak.
    Returns merged results from both sources.
    """
    contexts = []
    cur, model = get_supabase_client()
    query_embedding = model.encode([query])[0].tolist()
   
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
    for row in results:
        id_, content, metadata = row
        contexts.append({
            "content": content,
            "source": metadata.get("source_file", "supabase_db"),
            "region": metadata.get("region", "unknown"),
            "type": "supabase"
        })
    supabase_results_count = len(results)
    supabase_has_good_results = (
        supabase_results_count >= 2
        and any(len(doc["content"]) > 200 for doc in contexts)
    )
   
    if not supabase_has_good_results:
        print(f"[INFO] Supabase results weak — searching web for: '{query}'")
        try:
            with DDGS() as ddgs:
                ddgs_results = ddgs.text(query, max_results=top_k)
                for r in ddgs_results:
                    contexts.append({
                        "content": r.get("body", "")[:2000],
                        "source": r.get("href", "web_search"),
                        "region": region or "global",
                        "type": "web"
                    })
                    time.sleep(0.5)
        except Exception as e:
            print(f"[ERROR] Web search failed: {e}")
    print(f"[INFO] Retrieved {len(contexts)} contexts "
          f"({supabase_results_count} from Supabase, {len(contexts)-supabase_results_count} from web)")
    return contexts[:top_k]
def predict_health_risk(context: str, question: str) -> Dict:
    """
    Uses BioGPT for medical knowledge + Gemini for JSON formatting.
    Handles missing context gracefully.
    """
    try:
        model, tokenizer = get_bio_gpt()
        prompt = f"""
You are a medical expert. Answer the question using the context below.
If the context is incomplete, make reasonable inferences based on general medical knowledge of war zones.
Do NOT say "no information found" — provide the best possible answer.
Question: {question}
Context (first 800 chars): {context[:800]}
Answer in 2-3 sentences.
"""
        inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)
        if torch.cuda.is_available():
            inputs = {k: v.to("cuda") for k, v in inputs.items()}
        outputs = model.generate(
            **inputs,
            max_new_tokens=200,
            num_return_sequences=1,
            temperature=0.7,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id
        )
        bio_gpt_answer = tokenizer.decode(outputs[0], skip_special_tokens=True)
        print(f":stethoscope: BioGPT Raw Answer:\n{bio_gpt_answer}\n{'='*50}")
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
        import google.generativeai as genai
        genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
        gemini_model = genai.GenerativeModel('gemini-1.5-flash')
        gemini_response = gemini_model.generate_content(gemini_prompt)
        gemini_text = gemini_response.text.strip()
        print(f"Gemini Formatted Output:\n{gemini_text}\n{'='*50}")
        json_match = re.search(r'\{.*\}', gemini_text, re.DOTALL)
        if not json_match:
            raise ValueError("Gemini did not return JSON")
        json_str = json_match.group(0)
        json_str = json_str.replace("'", '"')
        json_str = re.sub(r',\s*([\}\]])', r'\1', json_str)
        parsed = json.loads(json_str)
        output = {
            "risk_level": "Unknown",
            "diseases": ["General morbidity"],
            "reason": "Post-conflict health risks",
            "recommendations": ["Conduct health assessment", "Strengthen surveillance"]
        }
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
        if not isinstance(output["diseases"], list):
            output["diseases"] = [str(output["diseases"])]
        if not isinstance(output["recommendations"], list):
            output["recommendations"] = [str(output["recommendations"])]
        return output
    except Exception as e:
        print(f"Final Error: {e}")
        return {
            "risk_level": "High",
            "diseases": ["Unknown risks"],
            "reason": "Data retrieval failed — assume worst-case scenario",
            "recommendations": ["Deploy emergency medical teams", "Initiate rapid assessment"]
        }





