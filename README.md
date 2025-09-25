# Tesfa AI - Health Risk Prediction Agent

Tesfa AI is an intelligent agent that predicts long-term health risks in post-conflict and active conflict regions using RAG (Retrieval Augmented Generation) and local BioGPT models.

## Features

- **Conflict-focused health risk assessment** for regions like Yemen, Syria, South Sudan, Ukraine, Gaza, Sudan
- **RAG-powered context retrieval** from Supabase database and web search
- **BioGPT integration** for medical knowledge and analysis  
- **Gemini AI formatting** for structured JSON responses
- **RESTful API** built with FastAPI and Google ADK
- **Web interface** for interactive queries

## Quick Start

### Prerequisites

- Python 3.11+
- Google API Key (for Gemini AI)
- Optional: Supabase database for context storage

### Installation

1. Clone the repository:
```bash
git clone https://github.com/akirachix/tesfa-ai.git
cd tesfa-ai
```

2. Install dependencies:
```bash
pip install -r tesfa_agent/requirements.txt
```

3. Set environment variables:
```bash
export GOOGLE_API_KEY="your-google-api-key"
# Optional Supabase configuration:
export SUPABASE_HOST="your-supabase-host"
export SUPABASE_DB="your-database"  
export SUPABASE_USER="your-username"
export SUPABASE_PASSWORD="your-password"
```

4. Start the server:
```bash
python main.py
```

The API will be available at `http://localhost:8080`

## API Usage

### Correct Request Format (JSON)

```bash
curl -X POST -H 'Content-Type: application/json' \
  -d '{"query": "What are the health risks in Yemen?"}' \
  http://localhost:8080/api/chat
```

### Example Response

```json
{
  "title": "Health Risk Alert: Yemen",
  "description": "High disease risks due to ongoing conflict",
  "country_name": "Yemen",
  "region_name": "National", 
  "disease_risks": [
    {
      "disease": "cholera",
      "risk_percentage": 85,
      "level": "high"
    }
  ],
  "high_risk_flag": true,
  "recommendations": [
    "Deploy emergency medical teams",
    "Strengthen disease surveillance"
  ]
}
```

## API Error Handling

If you accidentally send form-encoded data instead of JSON, you'll get a helpful error message:

```json
{
  "error": "Invalid request format",
  "message": "Request body should be JSON format, not form-encoded data.",
  "received_form_data": {"query": "hello"},
  "expected_format": "Send JSON in request body, e.g., {\"query\": \"your question here\"}",
  "curl_example": "curl -X POST -H 'Content-Type: application/json' -d '{\"query\":\"your question\"}' /endpoint"
}
```

## Testing

Run the included test script to verify your setup:

```bash
python test_api.py
```

This will test both correct and incorrect request formats.

## Architecture

- **main.py**: FastAPI application with Google ADK integration
- **tesfa_agent/agent.py**: LLM agent configuration with Gemini 2.0 Flash
- **tesfa_agent/tools.py**: RAG retrieval and BioGPT health risk prediction
- **Custom error handling** for better developer experience

## Development

### Project Structure

```
tesfa-ai/
├── main.py                          # FastAPI app entry point
├── tesfa_agent/
│   ├── agent.py                     # LLM agent definition  
│   ├── tools.py                     # RAG and prediction tools
│   └── requirements.txt             # Python dependencies
├── test_api.py                      # API testing script
├── PYDANTIC_FIX_DOCUMENTATION.md   # Error handling details
└── README.md                        # This file
```

### Recent Improvements

- **Fixed Pydantic validation error**: Added custom exception handler for form-data requests
- **Better error messages**: Clear explanations when wrong request format is used
- **Developer-friendly responses**: Include examples and curl commands in error responses

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`  
3. Make your changes and add tests
4. Commit your changes: `git commit -m 'Add feature'`
5. Push to the branch: `git push origin feature-name`
6. Submit a pull request

## License

[Add your license information here]

## Support

- 📚 Documentation: See `PYDANTIC_FIX_DOCUMENTATION.md` for API error handling details
- 🧪 Testing: Run `python test_api.py` to validate your setup
- 🐛 Issues: Report bugs via GitHub Issues
- 💬 Questions: [Add your support channels here]