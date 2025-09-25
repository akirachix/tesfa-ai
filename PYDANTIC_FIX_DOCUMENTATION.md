# Fix for Pydantic Validation Error

## Problem Description

The Tesfa AI API was returning a cryptic Pydantic validation error when clients sent form-encoded data instead of JSON:

```json
{
    "detail": [
        {
            "type": "model_attributes_type",
            "loc": ["body"],
            "msg": "Input should be a valid dictionary or object to extract fields from",
            "input": "query=hello%0A"
        }
    ]
}
```

## Root Cause

- The Google ADK (Agent Development Kit) framework generates FastAPI endpoints that expect JSON request bodies
- Pydantic models used for request validation expect dictionary/object data structures
- When clients send URL-encoded form data (`application/x-www-form-urlencoded`), Pydantic receives a string instead of a dictionary
- The error message was unhelpful for developers trying to understand the correct format

## Solution

Added a custom `RequestValidationError` exception handler in `main.py` that:

1. **Detects** the specific validation error for form-encoded data
2. **Parses** the URL-encoded data to show what was received
3. **Provides** a helpful error message with clear instructions
4. **Includes** examples of the correct JSON format and curl usage

## Implementation Details

### Custom Exception Handler

```python
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Check for the specific model_attributes_type error
    for error in exc.errors():
        if (error.get("type") == "model_attributes_type" and 
            error.get("msg") == "Input should be a valid dictionary or object to extract fields from"):
            
            # Parse form data and provide helpful response
            raw_input = error.get("input", "")
            if isinstance(raw_input, str) and "=" in raw_input:
                # Parse and return helpful error message
```

### New Error Response Format

```json
{
  "error": "Invalid request format",
  "message": "Request body should be JSON format, not form-encoded data.",
  "received_form_data": {
    "query": "hello\n"
  },
  "expected_format": "Send JSON in request body, e.g., {\"query\": \"your question here\"}",
  "curl_example": "curl -X POST -H 'Content-Type: application/json' -d '{\"query\":\"your question\"}' /endpoint"
}
```

## Benefits

1. **Better Developer Experience**: Clear error messages explain exactly what's wrong
2. **Faster Debugging**: Shows the parsed form data so developers can see what was sent
3. **Educational**: Provides examples of correct usage
4. **Backward Compatible**: Other validation errors continue to work normally
5. **Minimal Code Change**: Small addition to main.py without modifying core functionality

## Testing

The fix was validated with:
- Form data parsing logic verification  
- Error handler simulation tests
- Syntax validation of main.py
- Integration testing scenarios

## Usage Examples

### Incorrect (causes the error):
```bash
curl -X POST -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'query=hello' http://localhost:8080/api/endpoint
```

### Correct:
```bash
curl -X POST -H 'Content-Type: application/json' \
  -d '{"query": "hello"}' http://localhost:8080/api/endpoint
```

## Future Considerations

If form-encoded data support is needed in the future, consider:
1. Adding middleware to convert form data to JSON before validation
2. Creating custom Pydantic validators that accept both formats
3. Using FastAPI's `Form` dependency for specific endpoints that need form support

This fix maintains the current JSON-only API contract while providing much better error messages for common mistakes.