# Tesfa AI Architecture Documentation

## System Architecture Overview

Tesfa AI is a multi-layered health risk prediction system designed for conflict-affected regions. This document explains the architectural decisions, data flow, and technical implementation details.

## High-Level Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                        Client Layer                           │
│  - Web Browser (built-in UI)                                  │
│  - HTTP API Clients (REST/JSON)                               │
│  - Mobile Apps (via API)                                      │
└────────────────────┬─────────────────────────────────────────┘
                     │ HTTP/HTTPS
┌────────────────────▼─────────────────────────────────────────┐
│                     FastAPI Server                            │
│  ┌────────────────────────────────────────────────────────┐  │
│  │           Google ADK Framework                         │  │
│  │  - Request routing                                     │  │
│  │  - Session management (SQLite)                         │  │
│  │  - CORS handling                                       │  │
│  │  - Web UI serving                                      │  │
│  └────────────────────┬───────────────────────────────────┘  │
│                       │                                       │
│  ┌────────────────────▼───────────────────────────────────┐  │
│  │              Tesfa AI Agent                            │  │
│  │  ┌──────────────────────────────────────────────────┐  │  │
│  │  │        Gemini 2.5 Flash (LLM)                    │  │  │
│  │  │  - Conversation understanding                    │  │  │
│  │  │  - Response generation                           │  │  │
│  │  │  - Tool orchestration                            │  │  │
│  │  └────────┬──────────────────────────┬──────────────┘  │  │
│  │           │                          │                  │  │
│  │  ┌────────▼──────────┐    ┌─────────▼──────────────┐  │  │
│  │  │  retrieve_context │    │ predict_health_risk    │  │  │
│  │  │  (Tool #1)        │    │ (Tool #2)              │  │  │
│  │  └────────┬──────────┘    └─────────┬──────────────┘  │  │
│  └───────────┼───────────────────────────┼──────────────┘  │
└──────────────┼───────────────────────────┼─────────────────┘
               │                           │
        ┌──────▼────────┐          ┌──────▼───────────┐
        │               │          │                  │
┌───────▼────────┐  ┌──▼────────┐ │  ┌──────────────▼──┐
│   Supabase     │  │ DuckDuckGo│ │  │   BioGPT Model  │
│   PostgreSQL   │  │  Search   │ │  │  (microsoft/)   │
│   + pgvector   │  │  (Web)    │ │  │                 │
│                │  │           │ │  │  ┌──────────────┤
│  - Embeddings  │  │ Fallback  │ │  │  Gemini 2.5    │
│  - Documents   │  │ when DB   │ │  │  Flash         │
│  - Metadata    │  │ results   │ │  │  (Formatter)   │
└────────────────┘  │ are weak  │ │  └─────────────────┘
                    └───────────┘ │
                                  │
                    ┌─────────────▼──────────────┐
                    │  Sentence Transformers     │
                    │  (all-MiniLM-L6-v2)        │
                    │  - Query encoding          │
                    │  - Embedding generation    │
                    └────────────────────────────┘
```

## Component Details

### 1. FastAPI Server (main.py)

**Purpose**: HTTP server and request handling

**Technology Stack**:
- FastAPI: Modern Python web framework
- Uvicorn: ASGI server
- Google ADK: Agent orchestration framework

**Key Functions**:
- Serve web interface at `/`
- Handle API requests at `/api/chat`
- Manage WebSocket connections for real-time chat
- Store session state in SQLite database

**Configuration**:
```python
PORT = 8080 (default, can be overridden)
SESSION_DB = sqlite:///./sessions.db
CORS = Allow all origins (configurable)
WEB_UI = Enabled
```

### 2. Tesfa AI Agent (agent.py)

**Purpose**: Core AI agent that orchestrates the health risk assessment

**LLM**: Gemini 2.5 Flash
- **Why Gemini?** Fast inference, excellent JSON generation, cost-effective
- **Context Window**: 1M tokens (handles large documents)
- **Output**: Both conversational and structured JSON

**Tools Available**:
1. `retrieve_context()` - RAG retrieval
2. `predict_health_risk()` - Medical AI analysis

**Agent Behavior** (defined in prompt.py):
- Greets users with standardized message
- Determines if JSON or conversational response needed
- Validates region is conflict-affected
- Generates structured assessments when requested
- Provides actionable recommendations

### 3. Tool #1: retrieve_context (tools.py)

**Purpose**: Hybrid Retrieval-Augmented Generation (RAG) system

**Retrieval Strategy**:

#### Primary Source: Supabase Vector Database
```python
Query Encoding:
  User Query → SentenceTransformer → 384-dim vector

Vector Search:
  Query Vector → pgvector <-> operator → Top 3 similar docs
  
Results Include:
  - Content: Full text of document
  - Metadata: Source file, region, date
  - Score: Similarity score (implicit in ordering)
```

**Database Schema**:
```sql
CREATE TABLE embeddings (
  id SERIAL PRIMARY KEY,
  content TEXT NOT NULL,              -- Document text
  embedding VECTOR(384) NOT NULL,     -- SentenceTransformer embedding
  metadata JSONB                      -- {source_file, region, date, ...}
);

-- Vector similarity index
CREATE INDEX ON embeddings USING ivfflat (embedding vector_cosine_ops);
```

#### Fallback Source: Web Search (DuckDuckGo)

**When Triggered**:
- Less than 2 Supabase results, OR
- All Supabase results are short (<200 chars)

**Implementation**:
```python
with DDGS() as ddgs:
    results = ddgs.text(query, max_results=3)
    # Returns: title, body, href
    # Rate limited: 0.5s between requests
```

**Why This Hybrid Approach?**
- Supabase provides curated, high-quality conflict health data
- Web search ensures coverage for recent events or sparse regions
- Dual sources improve robustness and recall

**Output Format**:
```json
[
  {
    "content": "Yemen's healthcare system has collapsed...",
    "source": "yemen_health_report_2024.pdf",
    "region": "Sana'a",
    "type": "supabase"
  },
  {
    "content": "Recent cholera outbreak in...",
    "source": "https://reliefweb.int/...",
    "region": "global",
    "type": "web"
  }
]
```

### 4. Tool #2: predict_health_risk (tools.py)

**Purpose**: Two-stage medical AI analysis pipeline

#### Stage 1: BioGPT Medical Reasoning

**Model**: microsoft/BioGPT
- **Training Data**: 15M PubMed abstracts (biomedical literature)
- **Parameters**: 1.5B parameters
- **Domain**: Specialized in medical/clinical text

**Why BioGPT?**
- Domain expertise in medicine and public health
- Understands medical terminology and disease mechanisms
- Better than general LLMs for clinical reasoning

**Inference Process**:
```python
Prompt Template:
  "You are a medical expert. Answer using context below.
   Question: {user_question}
   Context: {retrieved_docs}
   Answer in 2-3 sentences."

Generation Parameters:
  max_new_tokens = 200
  temperature = 0.7 (balanced creativity/consistency)
  do_sample = True (stochastic generation)

Output: Unstructured medical analysis text
```

**GPU vs CPU**:
- GPU: ~2-5 seconds per request
- CPU: ~10-30 seconds per request
- Automatically uses GPU if available

#### Stage 2: Gemini JSON Formatting

**Model**: Gemini 2.5 Flash (same as main agent)

**Why Gemini for Formatting?**
- Excellent at structured output generation
- Faster than running BioGPT again
- Reliable JSON parsing with few hallucinations

**Conversion Process**:
```python
Prompt Template:
  "Convert this medical answer to JSON:
   {biogpt_output}
   
   Required keys:
   - risk_level: Low/Medium/High/Critical
   - diseases: [list of disease names]
   - reason: 1-sentence summary
   - recommendations: [2-3 actionable steps]"

JSON Extraction:
  1. Use regex to find JSON block
  2. Clean formatting (quotes, trailing commas)
  3. Parse with json.loads()
  4. Validate and add defaults if needed
```

**Fallback Handling**:
```python
If ANY step fails:
  return {
    "risk_level": "High",  # Assume worst case
    "diseases": ["Unknown risks"],
    "reason": "Data retrieval failed",
    "recommendations": ["Deploy emergency teams", ...]
  }
```

This ensures humanitarian organizations always get a response, even if technical failures occur.

### 5. Data Models and Embeddings

#### SentenceTransformer: all-MiniLM-L6-v2

**Specifications**:
- Dimensions: 384
- Model Size: ~80MB
- Speed: ~2000 sentences/second (CPU)

**Why This Model?**
- Lightweight and fast
- Good balance of quality and performance
- Efficient for real-time embedding

**Embedding Process**:
```python
text = "What are cholera risks in Yemen?"
vector = model.encode([text])[0]  # Shape: (384,)
# Use for similarity search in Supabase
```

#### BioGPT Model Loading

**Download Size**: ~1.6GB
**Cache Location**: `~/.cache/huggingface/`
**Load Time**: 30-120 seconds (first run only)

**Memory Requirements**:
- CPU: ~2-3GB RAM
- GPU: ~2GB VRAM (CUDA)

### 6. System Prompt and Behavior (prompt.py)

The system prompt is the "constitution" of the agent. It defines:

#### Scope Definition
```
Conflict-affected regions ONLY:
- Yemen, Syria, South Sudan, Ukraine, Gaza, Sudan
- Other active/post-conflict areas (validated by data)

Excluded:
- Stable countries (returns empty assessment)
```

#### Response Mode Logic
```python
if "JSON" in user_query or "in JSON format" in user_query:
    return structured_json_response()
else:
    return conversational_response()
```

#### Risk Assessment Rules
```
Risk Score (0-100%):
  0-30%   = Low risk (monitoring)
  31-70%  = Medium risk (intervention)
  71-100% = High risk (urgent action)

High Risk Flag:
  ANY disease >70% → high_risk_flag = True
```

#### JSON Structure Enforcement
```json
{
  "title": "Health Risk Alert: {Country}",
  "description": "Overview or 'not conflict-affected' message",
  "country_name": "Standardized English name",
  "region_name": "Subnational area or 'National'",
  "disease_risks": [
    {
      "disease": "Cholera",
      "risk_score": 75,
      "risk_level": "high"
    }
  ],
  "high_risk_flag": true/false,
  "recommendations": [
    "Deploy mobile health clinics",
    "Establish WASH programs",
    ...
  ]
}
```

## Data Flow Example

### Complete Request Flow

```
1. User Input:
   "What are health risks in Yemen in JSON format?"

2. FastAPI receives request:
   POST /api/chat
   Body: {"message": "What are health risks...", "session_id": "123"}

3. Google ADK routes to Tesfa Agent:
   - Loads session history
   - Appends user message
   - Invokes Gemini 2.5 Flash

4. Agent analyzes query:
   - Detects: "in JSON format" → JSON response needed
   - Detects: "Yemen" → conflict-affected (valid)
   - Detects: "health risks" → needs context

5. Agent calls Tool #1: retrieve_context("health risks Yemen")
   
   a. Supabase Query:
      - Encode: "health risks Yemen" → [0.23, -0.45, ...]
      - Search: SELECT ... ORDER BY embedding <-> [...]
      - Returns: 3 docs about Yemen health, cholera, malnutrition
   
   b. Web Search (if needed):
      - DuckDuckGo: "health risks Yemen"
      - Returns: Recent news articles
   
   Combined Contexts: [doc1, doc2, doc3]

6. Agent calls Tool #2: predict_health_risk(contexts, question)
   
   a. BioGPT Analysis:
      - Input: contexts + question
      - Output: "Yemen faces high cholera risk due to water infrastructure 
                 collapse. Malnutrition is critical in northern regions..."
   
   b. Gemini Formatting:
      - Input: BioGPT text
      - Output: Structured JSON with diseases, scores, recommendations

7. Agent compiles final response:
   - Follows prompt rules
   - Generates JSON with 4-6 diseases
   - Includes recommendations for each medium/high risk
   - Sets high_risk_flag based on scores

8. FastAPI returns response:
   - Stores in session
   - Returns JSON to client

9. Client displays:
   - Web UI: Renders formatted JSON
   - API client: Processes programmatically
```

## Performance Characteristics

### Latency Breakdown

**Typical Request (with warm models)**:
```
FastAPI overhead:        ~50ms
Agent reasoning:         ~500-1000ms
Tool #1 (retrieval):     ~200-500ms
  - Supabase query:      ~100-200ms
  - Embedding encode:    ~50ms
  - Web search:          ~200-300ms (if triggered)
Tool #2 (prediction):    ~3000-5000ms
  - BioGPT inference:    ~2000-4000ms (CPU) or ~500-1000ms (GPU)
  - Gemini formatting:   ~1000ms
Final response:          ~100ms

Total: 4-7 seconds (CPU), 2-3 seconds (GPU)
```

**Cold Start (first request after deployment)**:
```
BioGPT download:         ~60-120 seconds (one-time)
Model loading:           ~30-60 seconds
First request:           ~90-180 seconds total
Subsequent requests:     4-7 seconds (normal)
```

### Scalability Considerations

**Bottlenecks**:
1. BioGPT inference (CPU-bound)
2. Supabase connection pool size
3. Gemini API rate limits

**Solutions**:
- Use GPU for BioGPT (5-10x speedup)
- Increase Supabase connection pool
- Implement request queuing for high traffic
- Cache common queries (Redis)

**Concurrent Request Handling**:
- Models are loaded globally (shared across requests)
- Each request uses same model instance
- Thread-safe (Python GIL + PyTorch thread safety)
- Limit: ~5-10 concurrent requests (CPU), ~20-50 (GPU)

## Security Architecture

### API Key Management
```python
GOOGLE_API_KEY:  Required for Gemini API
SUPABASE_*:      Required for database access
All via environment variables (never in code)
```

### Network Security
- HTTPS required in production
- CORS configurable per domain
- No public database access (Supabase connection only)

### Container Security
- Non-root user (myuser)
- Minimal base image (python:3.11-slim)
- No shell access in container
- Read-only filesystem (except /tmp, /app)

### Data Privacy
- No PHI (Protected Health Information) stored
- Session data isolated per user
- Temporary data cleared after response
- No logging of sensitive data

## Error Handling Strategy

### Graceful Degradation
```python
Level 1: Supabase fails → Use web search
Level 2: BioGPT fails → Use Gemini only
Level 3: Gemini fails → Return fallback JSON
Level 4: All fails → Return worst-case scenario
```

### Error Messages
- User-facing: Generic, non-technical
- Logs: Detailed for debugging
- Sentry/monitoring: Structured error reports

## Monitoring and Observability

### Key Metrics to Track
```
- Request latency (p50, p95, p99)
- Tool call success rate
- Model inference time
- Database query performance
- API rate limit usage
- Error rates by type
```

### Logging Strategy
```python
Startup logs:
  - Environment config
  - Model loading status
  - Database connection

Request logs:
  - Query text (sanitized)
  - Tool calls made
  - Response time
  - Error traces (if any)
```

## Future Architecture Improvements

### Short-term
1. Add caching layer (Redis) for common queries
2. Implement request queuing for load management
3. Add health check endpoints
4. Improve error reporting

### Long-term
1. Multi-model ensemble (combine multiple medical LLMs)
2. Fine-tune BioGPT on conflict health data
3. Add real-time data ingestion pipeline
4. Implement feedback loop for model improvement
5. Build mobile app with offline mode

## Deployment Architecture

### Google Cloud Run
```yaml
Service: tesfa-ai
Region: us-central1
CPU: 2 vCPU
Memory: 4GB
Min instances: 0 (scales to zero)
Max instances: 10
Container: gcr.io/project/tesfa-ai:latest
Environment:
  - GOOGLE_API_KEY
  - SUPABASE_*
```

### Docker Container
```dockerfile
Base: python:3.11-slim
Size: ~2.5GB (includes PyTorch + models)
Startup: ~30-60 seconds (model loading)
Health check: GET /health
```

## Testing Strategy

### Unit Tests
- Test each tool independently
- Mock external dependencies (Supabase, DuckDuckGo)
- Validate JSON structure

### Integration Tests
- Full request flow
- Real API calls (staging environment)
- Session management

### Load Tests
- 100 concurrent users
- Sustained load (1 hour)
- Peak traffic simulation

---

**Last Updated**: November 2025
**Version**: 1.0
**Maintainer**: AkiraChix Team
