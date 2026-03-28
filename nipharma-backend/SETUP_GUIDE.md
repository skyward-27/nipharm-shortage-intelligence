# Nipharma Backend - Complete Setup Guide

Step-by-step guide to get the Nipharma FastAPI backend running locally and deployed.

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Git (for version control)
- A Groq API key (https://console.groq.com/keys)
- A NewsAPI key (https://newsapi.org/)

## Quick Start (5 minutes)

### 1. Get API Keys

**Groq API Key:**
1. Visit https://console.groq.com/keys
2. Sign up or log in
3. Create a new API key
4. Copy the key (you'll need it in step 4)

**NewsAPI Key:**
1. Visit https://newsapi.org/
2. Sign up for free account
3. Get your API key from dashboard
4. Copy the key (you'll need it in step 4)

### 2. Navigate to Project Directory

```bash
cd "/Users/chaitanyawarhade/Documents/NPT Stock Inteligance Unit/nipharma-backend"
```

### 3. Setup Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate
# On Windows: venv\Scripts\activate
```

### 4. Configure Environment Variables

```bash
# Copy the example env file
cp .env.example .env

# Edit .env and add your API keys
# Use your favorite editor (nano, vim, VS Code, etc.)
nano .env
```

Add your keys:
```
GROQ_API_KEY=your_groq_api_key_here
NEWS_API_KEY=your_news_api_key_here
```

### 5. Install Dependencies

```bash
pip install -r requirements.txt
```

### 6. Start the Server

```bash
# Option A: Using the startup script (recommended)
chmod +x start.sh
./start.sh

# Option B: Direct uvicorn command
uvicorn server.main:app --reload
```

### 7. Test the API

**In your browser:**
- API Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health Check: http://localhost:8000/

**Using curl:**
```bash
curl http://localhost:8000/
```

## Detailed Setup Instructions

### Step 1: Get Groq API Key

1. Open https://console.groq.com/keys in your browser
2. Click "Sign Up" or "Log In"
3. Complete the registration process
4. You'll see your API keys dashboard
5. Click "Create API Key" or copy existing key
6. Your key will look like: `gsk_abcdef123456789...`

### Step 2: Get NewsAPI Key

1. Open https://newsapi.org/ in your browser
2. Click "Get API Key"
3. Sign up with email or Google
4. Verify your email
5. Your API key will be displayed on dashboard
6. Your key will look like: `abc123def456...`

### Step 3: Clone or Navigate to Repository

If you haven't cloned yet:
```bash
# Navigate to Documents
cd ~/Documents

# Project directory already created at:
cd "NPT Stock Inteligance Unit/nipharma-backend"
```

### Step 4: Create Python Virtual Environment

```bash
# Verify Python version
python3 --version  # Should be 3.8 or higher

# Create venv in project directory
python3 -m venv venv

# Activate it
source venv/bin/activate
```

You should see `(venv)` at the start of your terminal prompt.

### Step 5: Create .env File

```bash
# Make a copy of the example
cp .env.example .env

# Edit with your preferred editor
# macOS/Linux:
nano .env
# or
vim .env
# or use VS Code
code .env

# Windows:
notepad .env
```

**File contents:**
```
GROQ_API_KEY=gsk_your_actual_key_here
NEWS_API_KEY=your_actual_news_api_key_here
HOST=0.0.0.0
PORT=8000
ENVIRONMENT=development
```

### Step 6: Install Python Dependencies

```bash
# Make sure venv is activated
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Verify installation
pip list | grep fastapi
```

### Step 7: Run the Server

**Option A: Using the startup script (easiest)**
```bash
chmod +x start.sh  # Make it executable
./start.sh
```

**Option B: Direct command**
```bash
source venv/bin/activate
uvicorn server.main:app --reload
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Application startup complete
```

### Step 8: Test Your Installation

**Method 1: Browser**
1. Open http://localhost:8000/docs
2. You should see interactive API documentation
3. Try the "Health Check" endpoint (GET /)
4. Try the "Chat" endpoint with a test message

**Method 2: Command line**
```bash
# Health check
curl http://localhost:8000/

# Get news
curl "http://localhost:8000/news?limit=3"

# Chat
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "chat_history": []}'
```

## Troubleshooting

### Issue: "Python command not found"
**Solution:**
```bash
# Try python3 explicitly
python3 --version
python3 -m venv venv
```

### Issue: "venv not found"
**Solution:**
```bash
# Reinstall venv module
python3 -m pip install --upgrade pip
python3 -m venv venv
```

### Issue: "Permission denied" on start.sh
**Solution:**
```bash
chmod +x start.sh
./start.sh
```

### Issue: "GROQ_API_KEY not configured"
**Solution:**
1. Check .env file exists: `ls -la .env`
2. Verify it contains: `GROQ_API_KEY=your_key`
3. Make sure the key is valid at https://console.groq.com
4. Restart the server after updating .env

### Issue: "NEWS_API_KEY not configured"
**Solution:**
1. Verify .env has: `NEWS_API_KEY=your_key`
2. Check key is valid at https://newsapi.org/
3. Make sure you haven't used all API calls (free tier: 500/month)

### Issue: "ConnectionError" or "Failed to fetch news"
**Solution:**
1. Check your internet connection
2. Verify API key is active
3. Check NewsAPI quota: https://newsapi.org/account
4. Check Groq status: https://status.groq.com

### Issue: Port 8000 already in use
**Solution:**
```bash
# Use different port
uvicorn server.main:app --reload --port 8001

# Or kill the process on 8000
# macOS/Linux:
lsof -i :8000
kill -9 <PID>

# Windows:
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

### Issue: "ModuleNotFoundError: No module named 'fastapi'"
**Solution:**
```bash
# Activate venv
source venv/bin/activate

# Reinstall requirements
pip install -r requirements.txt
```

## Project Structure

```
nipharma-backend/
├── server/
│   ├── __init__.py           # Package initialization
│   ├── main.py               # FastAPI app and routes
│   ├── chat.py               # Groq integration
│   └── news.py               # NewsAPI integration
├── config.py                 # Configuration settings
├── requirements.txt          # Python dependencies
├── requirements-dev.txt      # Development dependencies
├── .env.example              # Environment template
├── .gitignore               # Git ignore rules
├── Procfile                 # Deployment config
├── start.sh                 # Startup script
├── README.md                # Project overview
├── SETUP_GUIDE.md           # This file
├── API_TESTING.md           # Testing documentation
├── DEPLOYMENT.md            # Deployment guide
└── venv/                    # Virtual environment (created by python3 -m venv)
```

## API Endpoints Quick Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check |
| POST | `/chat` | Chat with AI |
| GET | `/news` | Get pharma news |
| GET | `/news/supply-chain` | Get supply chain news |
| GET | `/news/search` | Search news |
| GET | `/drugs` | Search drugs |
| GET | `/concessions` | Get concessions |
| GET | `/signals` | Get market signals |

## Next Steps

1. **Test the API:**
   - Visit http://localhost:8000/docs
   - Try different endpoints
   - Read API_TESTING.md for detailed tests

2. **Integrate with Frontend:**
   - Update frontend to call `http://localhost:8000`
   - Enable CORS (already configured)
   - Test authentication flow

3. **Deploy to Production:**
   - Follow DEPLOYMENT.md
   - Choose Render, Heroku, or Railway
   - Set up environment variables
   - Monitor logs and performance

4. **Development:**
   - Review API_TESTING.md for testing strategies
   - Install dev dependencies: `pip install -r requirements-dev.txt`
   - Run tests: `pytest`

## Common Commands

```bash
# Activate virtual environment
source venv/bin/activate

# Deactivate virtual environment
deactivate

# Install all dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt

# Start development server
uvicorn server.main:app --reload

# Start with custom port
uvicorn server.main:app --reload --port 8001

# Run tests (after installing requirements-dev.txt)
pytest

# Format code
black server/

# Lint code
flake8 server/

# Check types
mypy server/
```

## Getting Help

1. **Check the logs:** Look at terminal output for error messages
2. **Read the docs:** Check README.md and API_TESTING.md
3. **Verify API keys:** Test at console.groq.com and newsapi.org
4. **Check network:** Ensure internet connection is working
5. **Review .env:** Make sure configuration is correct

## Security Notes

- Never commit .env file to git
- Keep API keys private and secure
- Use environment variables for all secrets
- Don't share API keys in chat or emails
- Rotate keys periodically
- Use .gitignore to prevent accidental commits

## Performance Tips

- Chat responses may take 2-10 seconds (normal)
- News queries take 1-5 seconds (API dependent)
- Use caching for frequently requested news
- Monitor API quotas to avoid rate limits
- Consider adding Redis for production caching

## Additional Resources

- FastAPI Documentation: https://fastapi.tiangolo.com/
- Groq API Documentation: https://console.groq.com/docs
- NewsAPI Documentation: https://newsapi.org/docs
- Python Virtual Environments: https://docs.python.org/3/tutorial/venv.html
- Uvicorn: https://www.uvicorn.org/

## Support & Questions

For issues or questions:
1. Check this guide for troubleshooting section
2. Review error messages in terminal output
3. Check API documentation at `/docs` endpoint
4. Verify API keys are valid and active
5. Ensure internet connection is stable

---

**Last Updated:** March 2026
**Backend Version:** 1.0.0
**Python:** 3.8+
