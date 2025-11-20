# Developer Guide - Tesfa AI

## Table of Contents
1. [Getting Started](#getting-started)
2. [Development Environment](#development-environment)
3. [Project Structure](#project-structure)
4. [Adding New Features](#adding-new-features)
5. [Testing](#testing)
6. [Debugging](#debugging)
7. [Common Issues](#common-issues)
8. [Best Practices](#best-practices)

## Getting Started

### Prerequisites
- Python 3.11 or higher
- Git
- PostgreSQL with pgvector extension (or Supabase account)
- Google Cloud account (for Gemini API)

### Initial Setup

```bash
# Clone the repository
git clone https://github.com/akirachix/tesfa-ai.git
cd tesfa-ai

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env  # Create this file first
# Edit .env with your credentials
```

### Environment Variables

Create a `.env` file in the project root:

```bash
# Required
GOOGLE_API_KEY=your_gemini_api_key_here

# Supabase Configuration
SUPABASE_HOST=db.yourproject.supabase.co
SUPABASE_DB=postgres
SUPABASE_USER=postgres
SUPABASE_PASSWORD=your_password_here

# Optional
PORT=8080
DEBUG=false
```

### Database Setup (Supabase)

1. Create a Supabase project at https://supabase.com
2. Enable pgvector extension:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

3. Create embeddings table:
```sql
CREATE TABLE embeddings (
  id SERIAL PRIMARY KEY,
  content TEXT NOT NULL,
  embedding VECTOR(384) NOT NULL,
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Create index for fast similarity search
CREATE INDEX ON embeddings USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);
```

4. Insert sample data (optional):
```sql
-- You'll need to generate embeddings first using SentenceTransformer
-- See scripts/populate_database.py (create this for your use case)
```

### Running the Application

```bash
# Development mode (with auto-reload)
uvicorn main:app --reload --port 8080

# Production mode
python main.py
```

Visit http://localhost:8080 to see the web interface.

## Development Environment

### Recommended IDE Setup

**VS Code Extensions**:
- Python (Microsoft)
- Pylance
- Docker
- GitLens
- Thunder Client (for API testing)

**VS Code settings.json**:
```json
{
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "python.formatting.provider": "black",
  "python.formatting.blackArgs": ["--line-length", "120"],
  "editor.formatOnSave": true
}
```

### Code Formatting

```bash
# Install dev dependencies
pip install black pylint pytest

# Format code
black . --line-length 120

# Lint code
pylint tesfa_agent/ main.py

# Type checking (optional)
pip install mypy
mypy tesfa_agent/
```

## Project Structure

```
tesfa-ai/
├── main.py                 # FastAPI application entry point
├── requirements.txt        # Python dependencies
├── Dockerfile             # Container configuration
├── README.md              # User documentation
├── ARCHITECTURE.md        # Technical architecture
├── DEVELOPER.md           # This file
│
├── tesfa_agent/           # Main agent package
│   ├── __init__.py       # Package initialization
│   ├── agent.py          # LlmAgent configuration
│   ├── prompt.py         # System instructions
│   ├── tools.py          # Custom tools (retrieve_context, predict_health_risk)
│   ├── root_agent.py     # Agent loader for ADK
│   └── root_agent.yaml   # Agent metadata (optional)
│
├── .github/              # GitHub configuration
│   └── workflows/
│       └── deploy-adk-agent.yml  # CI/CD pipeline
│
└── tests/                # Test suite (create this)
    ├── test_agent.py
    ├── test_tools.py
    └── test_integration.py
```

### Key Files Explained

**main.py**: 
- Application bootstrap
- FastAPI server setup
- Google ADK initialization

**tesfa_agent/agent.py**:
- Creates LlmAgent instance
- Registers tools
- Loads system prompt

**tesfa_agent/prompt.py**:
- Defines agent behavior
- Output format rules
- Risk assessment guidelines

**tesfa_agent/tools.py**:
- `retrieve_context()`: RAG retrieval
- `predict_health_risk()`: Medical AI analysis
- Model loading and caching

## Adding New Features

### Adding a New Tool

1. Define the tool function in `tesfa_agent/tools.py`:

```python
def my_new_tool(param1: str, param2: int) -> dict:
    """
    Tool description for the agent.
    
    Args:
        param1: Description of param1
        param2: Description of param2
        
    Returns:
        Dictionary with results
    """
    # Implementation
    return {"result": "success"}
```

2. Register the tool in `tesfa_agent/agent.py`:

```python
from .tools import retrieve_context, predict_health_risk, my_new_tool

health_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="TesfaAIAgent",
    description="...",
    instruction=instruction_text,
    tools=[retrieve_context, predict_health_risk, my_new_tool]  # Add here
)
```

3. Update the system prompt if needed (prompt.py)

4. Test the new tool:

```python
# In Python REPL or test file
from tesfa_agent.tools import my_new_tool
result = my_new_tool("test", 42)
print(result)
```

### Modifying the System Prompt

Edit `tesfa_agent/prompt.py`:

```python
instruction_text = """
[Existing instructions...]

New behavior rule:
- When users ask about X, do Y
- Format responses as Z

[Rest of instructions...]
"""
```

**Important**: 
- Keep instructions clear and concise
- Use examples to illustrate expected behavior
- Test thoroughly after changes

### Adding a New Disease

To add a new disease to risk assessments:

1. Update `prompt.py`:
```python
### Disease Risk Assessment (4–6 diseases)
For each disease like cholera, malaria, PTSD, measles, acute malnutrition, 
dengue, and [YOUR_NEW_DISEASE]:
```

2. Add disease-specific guidance:
```python
### [YOUR_NEW_DISEASE] Risk Factors:
- Factor 1
- Factor 2
- Threshold: X% if Y condition
```

3. Update test cases to include new disease

### Changing the LLM Model

To use a different Gemini model:

```python
# In tesfa_agent/agent.py
health_agent = LlmAgent(
    model="gemini-2.0-flash-exp",  # or "gemini-1.5-pro", etc.
    # ... rest of config
)
```

**Available Gemini models**:
- `gemini-2.5-flash` - Fast, cost-effective (current)
- `gemini-1.5-pro` - More capable, slower
- `gemini-2.0-flash-exp` - Experimental features

## Testing

### Manual Testing

**Test greeting**:
```bash
curl -X POST http://localhost:8080/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello"}'
```

**Test health risk query**:
```bash
curl -X POST http://localhost:8080/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What are health risks in Yemen in JSON format?"}'
```

**Test out-of-scope query**:
```bash
curl -X POST http://localhost:8080/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What are health risks in Germany?"}'
```

### Unit Testing

Create `tests/test_tools.py`:

```python
import pytest
from tesfa_agent.tools import retrieve_context, predict_health_risk

def test_retrieve_context():
    """Test context retrieval"""
    results = retrieve_context("cholera outbreak Yemen")
    assert len(results) > 0
    assert "content" in results[0]
    assert "source" in results[0]

def test_predict_health_risk():
    """Test health risk prediction"""
    context = "Yemen faces severe water shortages..."
    question = "What are the health risks?"
    
    result = predict_health_risk(context, question)
    assert "risk_level" in result
    assert "diseases" in result
    assert isinstance(result["diseases"], list)

# Run with: pytest tests/
```

### Integration Testing

Create `tests/test_integration.py`:

```python
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_chat_endpoint():
    """Test full chat flow"""
    response = client.post(
        "/api/chat",
        json={"message": "What are health risks in Syria in JSON format?"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
```

## Debugging

### Enable Debug Logging

Add to `main.py`:

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Debug BioGPT Issues

```python
# In tools.py, add debug prints
def predict_health_risk(context: str, question: str) -> Dict:
    print(f"DEBUG: Context length = {len(context)}")
    print(f"DEBUG: Question = {question}")
    
    model, tokenizer = get_bio_gpt()
    print(f"DEBUG: Model loaded on {next(model.parameters()).device}")
    
    # ... rest of function
```

### Debug Database Connection

```python
# Test Supabase connection
from tesfa_agent.tools import get_supabase_client

cur, model = get_supabase_client()
cur.execute("SELECT COUNT(*) FROM embeddings")
count = cur.fetchone()[0]
print(f"Total embeddings: {count}")
```

### Common Debugging Commands

```bash
# Check if models are downloaded
ls ~/.cache/huggingface/hub/

# Check PyTorch CUDA availability
python -c "import torch; print(torch.cuda.is_available())"

# Test Supabase connection
python -c "from tesfa_agent.tools import get_supabase_client; get_supabase_client()"

# Check API key
python -c "import os; print('Key set' if os.getenv('GOOGLE_API_KEY') else 'Key missing')"
```

## Common Issues

### Issue: "GOOGLE_API_KEY is not set"

**Solution**:
```bash
export GOOGLE_API_KEY="your_key_here"
# Or add to .env file
```

### Issue: BioGPT download is too slow

**Solution**:
- Use a proxy or VPN if in restricted region
- Download manually:
```python
from transformers import AutoModelForCausalLM
model = AutoModelForCausalLM.from_pretrained("microsoft/BioGPT")
# This caches the model for future use
```

### Issue: Supabase connection timeout

**Solution**:
- Check firewall settings
- Verify credentials in .env
- Test connection:
```bash
psql "postgresql://user:pass@host:5432/postgres?sslmode=require"
```

### Issue: Out of memory (OOM)

**Solution**:
- Reduce batch size in BioGPT
- Use CPU instead of GPU
- Increase container memory limit
- Clear cache periodically

### Issue: Web search failing

**Solution**:
- DuckDuckGo may rate-limit
- Increase delay between requests:
```python
time.sleep(1.0)  # Increase from 0.5s to 1.0s
```

## Best Practices

### Code Style

1. **Follow PEP 8**: Use black for formatting
2. **Type hints**: Add type annotations
```python
def my_function(param: str) -> dict:
    return {"result": param}
```

3. **Docstrings**: Use Google style
```python
def my_function(param: str) -> dict:
    """
    Brief description.
    
    Args:
        param: Description of parameter
        
    Returns:
        Description of return value
    """
```

### Performance

1. **Cache models globally**: Already implemented in tools.py
2. **Limit context length**: Truncate to avoid long inference times
3. **Use GPU when available**: Check `torch.cuda.is_available()`
4. **Connection pooling**: Reuse database connections

### Security

1. **Never commit secrets**: Use .env and .gitignore
2. **Validate inputs**: Sanitize user queries
3. **Rate limiting**: Add rate limits to API endpoints
4. **CORS**: Restrict origins in production

### Error Handling

1. **Always provide fallback**: Return worst-case scenario on failure
2. **Log errors**: Use proper logging, not print()
3. **User-friendly messages**: Don't expose technical details
4. **Retry logic**: For transient failures

### Testing

1. **Test edge cases**: Empty inputs, long texts, special characters
2. **Mock external services**: Don't rely on real APIs in tests
3. **Continuous testing**: Run tests before commits
4. **Coverage**: Aim for >80% code coverage

### Documentation

1. **Keep README updated**: Reflect current functionality
2. **Comment complex logic**: Explain why, not what
3. **API documentation**: Use FastAPI's auto-generated docs
4. **Version changes**: Document breaking changes

## Development Workflow

### Feature Development

1. Create feature branch:
```bash
git checkout -b feature/new-disease-support
```

2. Implement feature with tests:
```bash
# Edit code
# Write tests
pytest tests/
```

3. Format and lint:
```bash
black .
pylint tesfa_agent/
```

4. Commit with clear message:
```bash
git commit -m "Add support for tuberculosis risk assessment"
```

5. Push and create PR:
```bash
git push origin feature/new-disease-support
# Create PR on GitHub
```

### Release Process

1. Update version in `setup.py` or `__init__.py`
2. Update CHANGELOG.md
3. Create release tag:
```bash
git tag -a v1.1.0 -m "Release v1.1.0: Add new disease support"
git push origin v1.1.0
```

4. Deploy to production via CI/CD

## Resources

### External Documentation
- [Google ADK Docs](https://developers.google.com/adk)
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Supabase Docs](https://supabase.com/docs)
- [BioGPT Paper](https://arxiv.org/abs/2210.10341)

### Internal Resources
- README.md - User guide
- ARCHITECTURE.md - System design
- This file (DEVELOPER.md) - Development guide

### Getting Help

- **GitHub Issues**: For bugs and feature requests
- **Team Chat**: [Your communication channel]
- **Email**: [Team contact email]

## Contributing

See CONTRIBUTING.md for guidelines on:
- Code review process
- Pull request template
- Commit message format
- Branching strategy

---

**Happy Coding! 🚀**

For questions, contact the AkiraChix team.
