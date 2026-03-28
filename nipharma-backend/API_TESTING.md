# Nipharma Backend - API Testing Guide

Complete guide for testing all Nipharma API endpoints.

## Quick Start

1. **Start the server:**
   ```bash
   ./start.sh
   ```

2. **Open interactive API docs:**
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

## Testing Methods

### Method 1: Swagger UI (Recommended for beginners)
1. Go to http://localhost:8000/docs
2. Click on any endpoint to expand it
3. Click "Try it out"
4. Enter parameters and request body
5. Click "Execute"

### Method 2: cURL (Command Line)
```bash
curl -X GET "http://localhost:8000/" \
  -H "accept: application/json"
```

### Method 3: Python Requests
```python
import requests

response = requests.get("http://localhost:8000/")
print(response.json())
```

### Method 4: Postman (Desktop App)
1. Import the API endpoints
2. Create requests in Collections
3. Set variables for URLs
4. Run requests and view responses

## Endpoint Tests

### 1. Health Check Endpoint

**Endpoint:** `GET /`

**cURL:**
```bash
curl -X GET "http://localhost:8000/" \
  -H "accept: application/json"
```

**Expected Response:**
```json
{
  "status": "running",
  "version": "1.0.0",
  "groq_configured": true,
  "news_api_configured": true
}
```

**What It Tests:**
- API is running
- Both API keys are configured
- Server configuration is correct

---

### 2. Chat Endpoint

**Endpoint:** `POST /chat`

**Request Body:**
```json
{
  "message": "What are the current UK drug shortages?",
  "chat_history": []
}
```

**cURL:**
```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What are the current UK drug shortages?",
    "chat_history": []
  }'
```

**Expected Response:**
```json
{
  "response": "Based on current data, several medications are experiencing shortages in the UK...",
  "role": "assistant"
}
```

**Test Cases:**

1. **Simple Query:**
   ```json
   {
     "message": "Hello, what can you help me with?",
     "chat_history": []
   }
   ```

2. **With Chat History:**
   ```json
   {
     "message": "Tell me more about that",
     "chat_history": [
       {
         "role": "user",
         "content": "What is pharmaceutical supply chain?"
       },
       {
         "role": "assistant",
         "content": "The pharmaceutical supply chain refers to..."
       }
     ]
   }
   ```

3. **Domain-Specific Query:**
   ```json
   {
     "message": "What factors influence UK drug pricing?",
     "chat_history": []
   }
   ```

4. **Multi-Turn Conversation:**
   - First message: "What are drug shortages?"
   - Follow-up: "How do they affect the market?"
   - Follow-up: "What's the financial impact?"

**What It Tests:**
- Groq API integration working
- Chat history handling
- Response generation
- Error handling for empty messages

---

### 3. News Endpoint

**Endpoint:** `GET /news?limit=10`

**cURL:**
```bash
curl -X GET "http://localhost:8000/news?limit=5" \
  -H "accept: application/json"
```

**Expected Response:**
```json
{
  "success": true,
  "count": 5,
  "articles": [
    {
      "title": "UK Drug Shortage Crisis Deepens",
      "description": "NHS faces unprecedented shortages...",
      "url": "https://example.com/article1",
      "image": "https://example.com/image1.jpg",
      "source": "BBC News",
      "publishedAt": "2026-03-28T10:30:00Z",
      "author": "Jane Doe"
    }
  ]
}
```

**Test Cases:**

1. **Default Limit:**
   ```bash
   curl "http://localhost:8000/news"
   ```

2. **Custom Limit:**
   ```bash
   curl "http://localhost:8000/news?limit=20"
   ```

3. **Edge Cases:**
   ```bash
   curl "http://localhost:8000/news?limit=1"   # Minimum
   curl "http://localhost:8000/news?limit=50"  # Maximum
   ```

**What It Tests:**
- NewsAPI integration working
- Article formatting
- Pagination handling
- Error responses when API keys missing

---

### 4. Supply Chain News Endpoint

**Endpoint:** `GET /news/supply-chain?limit=10`

**cURL:**
```bash
curl -X GET "http://localhost:8000/news/supply-chain?limit=5" \
  -H "accept: application/json"
```

**Expected Response:**
Same structure as /news endpoint but with supply chain focused articles.

**What It Tests:**
- Targeted news queries working
- Different query parameters

---

### 5. News Search Endpoint

**Endpoint:** `GET /news/search?query=SEARCH_TERM&limit=10`

**cURL:**
```bash
curl -X GET "http://localhost:8000/news/search?query=drug%20shortage&limit=5" \
  -H "accept: application/json"
```

**URL Encoded Examples:**
- `drug shortage` → `drug%20shortage`
- `medicine price` → `medicine%20price`
- `pharmacy supply` → `pharmacy%20supply`

**Test Cases:**

1. **Single Word:**
   ```bash
   curl "http://localhost:8000/news/search?query=shortage"
   ```

2. **Multiple Words:**
   ```bash
   curl "http://localhost:8000/news/search?query=drug%20shortage%20UK"
   ```

3. **Specific Brand:**
   ```bash
   curl "http://localhost:8000/news/search?query=penicillin"
   ```

4. **Operator Queries:**
   ```bash
   curl "http://localhost:8000/news/search?query=supply%20AND%20chain"
   ```

**What It Tests:**
- Custom query handling
- URL encoding
- Search functionality

---

### 6. Drugs Endpoint (Placeholder)

**Endpoint:** `GET /drugs?search=SEARCH_TERM`

**cURL:**
```bash
curl -X GET "http://localhost:8000/drugs?search=paracetamol" \
  -H "accept: application/json"
```

**Expected Response:**
```json
{
  "message": "Drugs endpoint - coming soon",
  "search": "paracetamol",
  "status": "under_development"
}
```

**What It Tests:**
- Endpoint structure
- Query parameter passing

---

### 7. Concessions Endpoint (Placeholder)

**Endpoint:** `GET /concessions`

**cURL:**
```bash
curl -X GET "http://localhost:8000/concessions" \
  -H "accept: application/json"
```

**Expected Response:**
```json
{
  "message": "Concessions endpoint - coming soon",
  "status": "under_development"
}
```

---

### 8. Market Signals Endpoint (Placeholder)

**Endpoint:** `GET /signals`

**cURL:**
```bash
curl -X GET "http://localhost:8000/signals" \
  -H "accept: application/json"
```

**Expected Response:**
```json
{
  "message": "Market signals endpoint - coming soon",
  "signals": {
    "gbp_inr": "TBD",
    "brent_crude": "TBD",
    "boe_rate": "TBD"
  },
  "status": "under_development"
}
```

---

## Error Testing

### Test Missing API Keys

1. **Remove GROQ_API_KEY from .env**
   ```bash
   # Edit .env and comment out GROQ_API_KEY
   ```

2. **Test chat endpoint:**
   ```bash
   curl -X POST "http://localhost:8000/chat" \
     -H "Content-Type: application/json" \
     -d '{"message": "Hello", "chat_history": []}'
   ```

3. **Expected error:**
   ```json
   {
     "response": "Error communicating with Groq: ..."
   }
   ```

### Test Invalid Parameters

```bash
# Empty message
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "", "chat_history": []}'
# Expected: 400 Bad Request

# Invalid limit
curl "http://localhost:8000/news?limit=1000"
# Expected: 422 Unprocessable Entity (limit must be ≤ 50)

# Missing required query
curl "http://localhost:8000/news/search"
# Expected: 422 Unprocessable Entity (query required)
```

## Load Testing

### Using Apache Bench

```bash
# 100 requests, 10 concurrent
ab -n 100 -c 10 http://localhost:8000/

# Chat endpoint
ab -n 50 -c 5 -p payload.json -T application/json \
  http://localhost:8000/chat
```

### Using wrk

```bash
# Basic load test
wrk -t4 -c100 -d30s http://localhost:8000/

# With custom script
wrk -t4 -c100 -d30s -s script.lua http://localhost:8000/chat
```

## Performance Metrics

### Response Times to Expect

| Endpoint | Time | Notes |
|----------|------|-------|
| `/` | <50ms | Health check |
| `/news` | 1-5s | API call + formatting |
| `/news/search` | 1-5s | API call + formatting |
| `/chat` | 2-10s | Groq processing time |

### Monitor with:

```bash
# Real-time request logging
watch -n 1 'curl -s http://localhost:8000/ | jq'

# Check response headers
curl -i http://localhost:8000/

# Measure response time
time curl -s http://localhost:8000/news | head -c 100
```

## Automated Testing

### Python Script

```python
import requests
import json
from datetime import datetime

API_URL = "http://localhost:8000"

def test_health():
    response = requests.get(f"{API_URL}/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"
    print("✓ Health check passed")

def test_chat():
    payload = {
        "message": "What are drug shortages?",
        "chat_history": []
    }
    response = requests.post(f"{API_URL}/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert len(data["response"]) > 0
    print("✓ Chat endpoint passed")

def test_news():
    response = requests.get(f"{API_URL}/news", params={"limit": 5})
    assert response.status_code == 200
    data = response.json()
    assert "articles" in data
    print(f"✓ News endpoint passed - {data['count']} articles")

if __name__ == "__main__":
    print(f"Testing Nipharma API at {API_URL}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 50)

    test_health()
    test_chat()
    test_news()

    print("=" * 50)
    print("All tests passed!")
```

Run with:
```bash
python3 test_api.py
```

## Browser Testing

### Interactive Testing in Browser

1. **Swagger UI**
   ```
   http://localhost:8000/docs
   ```

2. **ReDoc**
   ```
   http://localhost:8000/redoc
   ```

3. **Simple GET in address bar**
   ```
   http://localhost:8000/
   http://localhost:8000/news
   http://localhost:8000/news?limit=3
   ```

## Debugging Tips

### Check Logs in Real-time
```bash
# Terminal running uvicorn shows request logs
# Look for:
# - Request method and path
# - Status code
# - Response time
# - Any errors
```

### Use Browser DevTools
1. Open http://localhost:8000/docs
2. Open Browser DevTools (F12)
3. Go to Network tab
4. Execute requests and inspect:
   - Request headers
   - Request body
   - Response headers
   - Response body
   - Timing

### Test with HTTPie (Friendlier than cURL)

```bash
# Install: pip install httpie

# Health check
http :8000/

# Chat
http POST :8000/chat \
  message="What is pharmaceutical supply?" \
  chat_history:=[]

# News
http :8000/news limit==5
```

## Common Issues and Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| 500 error on /chat | Invalid GROQ_API_KEY | Verify key in .env |
| Empty news articles | Invalid NEWS_API_KEY | Verify key in .env |
| Slow responses | API rate limit hit | Wait or upgrade API plan |
| CORS error | Frontend domain not allowed | Check CORS middleware settings |
| Connection refused | Server not running | Run `./start.sh` |

## Next Steps

Once all tests pass:
1. Test with frontend application
2. Set up monitoring/logging
3. Deploy to production
4. Monitor real-time performance

