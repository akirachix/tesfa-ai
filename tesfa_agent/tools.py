import os
import re
import json
import torch
import psycopg2
import time
import random
from typing import List, Dict, Optional
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModelForCausalLM
from duckduckgo_search import DDGS
from groq import Groq



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

def retrieve_context(query: str) -> List[Dict]:
    """
    Hybrid retriever: queries Supabase pgvector first,
    falls back to web search if results are weak.
    Returns merged results from both sources.
    """
    contexts = []
    cur, model = get_supabase_client()
    query_embedding = model.encode([query])[0].tolist()
    top_k = 3 
    region = None 
   
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

def call_llama_for_formatting(prompt: str, max_retries=3) -> str:
    """
    Calls Llama-3.1-8b via Groq with exponential backoff retry.
    Uses generic exception handling for maximum compatibility.
    """
    from groq import Groq  

    for attempt in range(max_retries + 1):
        try:
            client = Groq(api_key=os.environ["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"])
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=500,
                timeout=30
            )
            return response.choices[0].message.content.strip()

        except Exception as e:
           
            error_str = str(e).lower()
            is_retryable = (
                "503" in error_str or
                "service unavailable" in error_str or
                "429" in error_str or
                "rate limit" in error_str or
                "overloaded" in error_str or
                "timeout" in error_str
            )

            if is_retryable and attempt < max_retries:
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                print(f"[WARN] Groq retryable error (attempt {attempt + 1}/{max_retries + 1}): {e}. Retrying in {wait_time:.2f}s...")
                time.sleep(wait_time)
            else:
             
                raise e

def predict_health_risk(context: str, question: str) -> Dict:
    """
    Uses BioGPT for medical reasoning + Llama-3.1 (Groq) for JSON formatting.
    Handles missing context and API failures gracefully.
    """
    try:
       
        model, tokenizer = get_bio_gpt()
        prompt = f"""
You are a medical expert in humanitarian crises. Answer the question using the context below.
If context is limited, infer based on typical war-zone conditions (displacement, destroyed clinics, malnutrition).
Do NOT say "no data" — provide best possible expert judgment.
Question: {question}
Context (first 800 chars): {context[:800]}
Answer in 2-3 clear, factual sentences.
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
        print(f"[BioGPT] Raw Answer:\n{bio_gpt_answer}\n{'='*50}")

        llama_prompt = f"""
You are a humanitarian data formatter. Convert the following medical expert answer into a JSON object with these keys:
- "risk_level": one of "Low", "Medium", "High", or "Critical"
- "diseases": list of disease or health condition names (e.g., ["Cholera", "PTSD", "Untreated cleft lip"])
- "reason": one-sentence summary of why this is a risk in conflict settings
- "recommendations": list of 2-3 actionable, NGO-friendly steps

Medical Answer:
{bio_gpt_answer}

Rules:
- NEVER return empty lists. If diseases aren't named, infer plausible ones.
- Use war-zone logic: lack of care = high risk, even for congenital conditions.
- Output ONLY valid JSON. No markdown, no extra text.
"""
        formatted_output = call_llama_for_formatting(llama_prompt)
        print(f"[Llama-3.1] Formatted Output:\n{formatted_output}\n{'='*50}")


        json_match = re.search(r'\{.*\}', formatted_output, re.DOTALL)
        if not json_match:
            raise ValueError("Llama did not return JSON")

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
            "diseases": ["diseases", "disease", "conditions"],
            "reason": ["reason", "explanation"],
            "recommendations": ["recommendations", "actions", "steps"]
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
        print(f"[ERROR] Final failure in predict_health_risk: {e}")
        return {
            "risk_level": "High",
            "diseases": ["Service or data failure"],
            "reason": "Temporary system overload — using conservative conflict-zone assumptions",
            "recommendations": [
                "Assume high risk for infectious diseases and unmet surgical needs",
                "Deploy rapid health assessment team",
                "Prioritize WASH and maternal care"
            ]
        }