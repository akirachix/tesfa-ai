# Tesfa AI Agent 🏥🌍

**Tesfa AI Agent** is an AI-powered health risk prediction system designed specifically for post-conflict and active conflict regions. It combines Retrieval-Augmented Generation (RAG), local medical AI models (BioGPT), and Google's Gemini to provide actionable health risk assessments for humanitarian organizations.

## 🎯 Overview

Tesfa AI analyzes health risks in conflict-affected areas like Yemen, Syria, South Sudan, Ukraine, Gaza, and Sudan. The system:
- Predicts disease outbreaks and health risks based on conflict data
- Provides risk scores (0-100%) for diseases like cholera, malaria, PTSD, measles, malnutrition, and dengue
- Generates actionable recommendations for NGOs and humanitarian workers
- Uses a hybrid retrieval system (Supabase vector database + web search)
- Leverages BioGPT for medical reasoning and Gemini for structured output

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Tesfa AI Agent                           │
├─────────────────────────────────────────────────────────────┤
│  FastAPI Server (main.py)                                    │
│  ├─ Google ADK Framework                                     │
│  └─ Web Interface + API Endpoints                            │
├─────────────────────────────────────────────────────────────┤
│  Agent Layer (tesfa_agent/)                                  │
│  ├─ agent.py: LlmAgent configuration                         │
│  ├─ prompt.py: System instructions and behavior rules        │
│  └─ tools.py: Core functionality                             │
│     ├─ retrieve_context(): Hybrid RAG retrieval              │
│     │   ├─ Supabase pgvector (primary)                       │
│     │   └─ DuckDuckGo search (fallback)                      │
│     └─ predict_health_risk(): Medical AI analysis            │
│         ├─ BioGPT: Medical knowledge reasoning               │
│         └─ Gemini 2.5 Flash: JSON formatting                 │
├─────────────────────────────────────────────────────────────┤
│  Data & Models                                               │
│  ├─ Supabase PostgreSQL + pgvector                           │
│  ├─ SentenceTransformer (all-MiniLM-L6-v2)                   │
│  └─ Microsoft BioGPT                                          │
└─────────────────────────────────────────────────────────────┘
```

## 📦 Components Explained

### 1. **main.py** - Application Entry Point
- Initializes FastAPI server using Google ADK framework
- Configures CORS for cross-origin requests
- Enables web interface for chat-based interaction
- Uses SQLite for session management
- Checks PyTorch installation and CUDA availability on startup

### 2. **tesfa_agent/agent.py** - Agent Configuration
- Creates `LlmAgent` instance using Gemini 2.5 Flash model
- Registers custom tools (`retrieve_context`, `predict_health_risk`)
- Loads system instructions from `prompt.py`
- Checks for GOOGLE_API_KEY environment variable

### 3. **tesfa_agent/prompt.py** - System Behavior
Contains the AI agent's instruction manual:
- **Scope**: Only handles conflict-affected regions
- **Responses**: Conversational by default, JSON only when explicitly requested
- **Risk Assessment Rules**:
  - Risk scores: 0-100% (low: 0-30%, medium: 31-70%, high: 71-100%)
  - High-risk flag triggers at >70%
  - Returns empty assessment for stable countries
- **Output Format**: Structured JSON with disease risks, recommendations, and tasks

### 4. **tesfa_agent/tools.py** - Core Functionality

#### **retrieve_context(query: str)** - Hybrid RAG System
```python
# Step 1: Query Supabase vector database
# - Encodes query using SentenceTransformer
# - Finds top 3 most similar documents using pgvector
# - Returns: content, source, region, type

# Step 2: Fallback to web search (if Supabase results are weak)
# - Uses DuckDuckGo search API
# - Retrieves up to 3 web results
# - Respects rate limits (0.5s delay between requests)

# Returns: Combined list of contexts from both sources
```

#### **predict_health_risk(context: str, question: str)** - Medical AI Analysis
```python
# Step 1: BioGPT Analysis
# - Uses Microsoft's BioGPT for medical reasoning
# - Generates 2-3 sentence medical answer
# - Runs on GPU if available, otherwise CPU
# - Handles missing context gracefully

# Step 2: Gemini Formatting
# - Converts BioGPT output to structured JSON
# - Extracts: risk_level, diseases, reason, recommendations
# - Ensures lists are never empty (makes inferences if needed)

# Returns: Structured risk assessment
```

### 5. **requirements.txt** - Dependencies
Key packages:
- **google-adk**: Google Agent Developer Kit framework
- **google-genai**: Gemini API client
- **fastapi + uvicorn**: Web server
- **torch**: PyTorch for BioGPT
- **transformers**: Hugging Face models
- **sentence-transformers**: Text embeddings
- **chromadb**: Vector database support
- **psycopg2-binary**: PostgreSQL (Supabase) connection
- **duckduckgo-search**: Web search fallback

### 6. **Dockerfile** - Container Configuration
- Base: Python 3.11 slim
- Installs system dependencies (build-essential, ffmpeg)
- Uses CPU-only PyTorch for smaller image size
- Runs as non-root user for security
- Default port: 8080 (configurable via PORT env var)

## 🚀 Installation & Setup

### Prerequisites
- Python 3.11+
- PostgreSQL database with pgvector extension (Supabase recommended)
- Google API key for Gemini

### Environment Variables
Create a `.env` file with:
```bash
# Required
GOOGLE_API_KEY=your_gemini_api_key_here

# Supabase Configuration
SUPABASE_HOST=your_supabase_host
SUPABASE_DB=postgres
SUPABASE_USER=your_username
SUPABASE_PASSWORD=your_password

# Optional
PORT=8080
```

### Local Installation
```bash
# 1. Clone repository
git clone https://github.com/akirachix/tesfa-ai.git
cd tesfa-ai

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set environment variables
export GOOGLE_API_KEY="your_key_here"
export SUPABASE_HOST="your_host"
# ... (other env vars)

# 4. Run the server
python main.py
```

### Docker Deployment
```bash
# Build image
docker build -t tesfa-ai .

# Run container
docker run -p 8080:8080 \
  -e GOOGLE_API_KEY="your_key" \
  -e SUPABASE_HOST="your_host" \
  -e SUPABASE_DB="postgres" \
  -e SUPABASE_USER="your_user" \
  -e SUPABASE_PASSWORD="your_password" \
  tesfa-ai
```

## 🎮 Usage

### Web Interface
Navigate to `http://localhost:8080` to access the chat interface.

### Example Queries

**1. Conversational Query:**
```
User: "What are the health risks in Yemen?"
Agent: "Yemen faces severe health risks due to ongoing conflict..."
```

**2. JSON Request:**
```
User: "Assess health risks in Syria in JSON format"
Agent: {
  "title": "Health Risk Alert: Syria",
  "country_name": "Syria",
  "region_name": "Aleppo Governorate",
  "disease_risks": [
    {"disease": "Cholera", "risk_score": 75, "risk_level": "high"},
    {"disease": "PTSD", "risk_score": 85, "risk_level": "high"},
    ...
  ],
  "high_risk_flag": true,
  "recommendations": [
    "Deploy mobile health clinics",
    "Establish WASH programs",
    ...
  ]
}
```

**3. Out-of-Scope Query:**
```
User: "What are health risks in France?"
Agent: {
  "description": "This is not a conflict-affected area and the assessment is beyond my expertise.",
  "disease_risks": [],
  "high_risk_flag": false,
  ...
}
```

## 🔧 Configuration

### Supported Conflict Regions
- Yemen, Syria, South Sudan, Ukraine, Gaza, Sudan
- Other conflict-affected areas (determined by historical data)

### Disease Coverage
Primary diseases assessed:
- Cholera (waterborne)
- Malaria (vector-borne)
- PTSD (mental health)
- Measles (vaccine-preventable)
- Acute malnutrition
- Dengue (vector-borne)

### Risk Thresholds
- **Low**: 0-30% (monitoring needed)
- **Medium**: 31-70% (intervention recommended)
- **High**: 71-100% (urgent action required)

## 🛠️ Technical Details

### Model Selection
- **Gemini 2.5 Flash**: Fast, cost-effective, excellent JSON formatting
- **BioGPT**: Specialized in medical/biomedical text, pretrained on PubMed
- **all-MiniLM-L6-v2**: Lightweight sentence embeddings (384 dimensions)

### Database Schema (Supabase)
```sql
CREATE TABLE embeddings (
  id SERIAL PRIMARY KEY,
  content TEXT,
  embedding VECTOR(384),
  metadata JSONB
);

-- Metadata fields:
-- - source_file: origin document
-- - region: geographic area
-- - date: timestamp
```

### Performance Optimizations
- **Global model caching**: Models loaded once, reused across requests
- **GPU acceleration**: Automatic CUDA detection for BioGPT
- **Hybrid retrieval**: Fallback ensures data is always available
- **Connection pooling**: Reuses Supabase connection

## 🔐 Security & Privacy
- No secrets in code (environment variables only)
- Non-root Docker user
- CORS configured for controlled access
- Session data isolated per user
- No PHI (Protected Health Information) storage

## 🧪 Testing

### Manual Testing
```bash
# Start server
python main.py

# Test greeting
curl http://localhost:8080/api/chat -X POST \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello"}'

# Test health risk query
curl http://localhost:8080/api/chat -X POST \
  -H "Content-Type: application/json" \
  -d '{"message": "What are health risks in Yemen in JSON format?"}'
```

### Expected Startup Output
```
STARTUP: environment PORT=8080
STARTUP: torch import ok: 2.8.0 cuda_available= False
Connecting to Supabase Postgres...
[INFO] Connected to Supabase Postgres
Loading BioGPT model (this may take 1-2 minutes)...
BioGPT loaded on CPU.
```

## 📊 Data Flow

1. **User Query** → FastAPI endpoint
2. **Agent receives query** → Determines if JSON or conversational response
3. **Tool call: retrieve_context()** → Fetch relevant documents
   - Query Supabase vector DB
   - Fallback to web search if needed
4. **Tool call: predict_health_risk()** → Generate assessment
   - BioGPT analyzes medical context
   - Gemini formats as JSON
5. **Agent compiles response** → Follows prompt rules
6. **Response returned** → JSON or natural language

## 🌐 Deployment

### Google Cloud Run
```bash
gcloud run deploy tesfa-ai \
  --image gcr.io/your-project/tesfa-ai \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_API_KEY=xxx,SUPABASE_HOST=xxx,...
```

### Environment-Specific Files
- **.dockergitignore**: Exclude files from Docker context
- **.gcloudignore**: Exclude files from Cloud Build
- **.gitignore**: Standard Git exclusions

## 🤝 Contributing

This is an AkiraChix project. For contributions:
1. Fork the repository
2. Create a feature branch
3. Make minimal, focused changes
4. Test thoroughly
5. Submit a pull request

## 📝 License

[Specify your license here]

## 🆘 Troubleshooting

### "GOOGLE_API_KEY is not set"
- Add `GOOGLE_API_KEY` to your environment variables
- Check `.env` file if using one

### "Supabase connection failed"
- Verify Supabase credentials
- Ensure pgvector extension is installed
- Check network connectivity

### "BioGPT loading too slow"
- First run downloads ~1.6GB model from Hugging Face
- Subsequent runs load from cache (~/.cache/huggingface)
- Consider using GPU for faster inference

### "Web search failing"
- DuckDuckGo may rate-limit requests
- Increase delay between searches in tools.py
- Supabase should provide primary data source

## 🔗 Related Resources

- [Google ADK Documentation](https://developers.google.com/adk)
- [BioGPT Paper](https://arxiv.org/abs/2210.10341)
- [Supabase Docs](https://supabase.com/docs)
- [Sentence Transformers](https://www.sbert.net/)

## 📧 Contact

For questions or support, contact the AkiraChix team.

---

**Built with ❤️ for humanitarian impact in conflict-affected regions**
