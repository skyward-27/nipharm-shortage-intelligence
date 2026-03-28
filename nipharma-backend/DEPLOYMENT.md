# Nipharma Backend Deployment Guide

This guide covers deploying the Nipharma FastAPI backend to various platforms.

## Pre-Deployment Checklist

- [ ] Clone/pull the latest code
- [ ] Create `.env` file with API keys
- [ ] Test locally with `uvicorn server.main:app --reload`
- [ ] All endpoints returning expected responses
- [ ] Chat and News APIs functioning

## Local Testing

```bash
cd /Users/chaitanyawarhade/Documents/NPT\ Stock\ Inteligance\ Unit/nipharma-backend
source venv/bin/activate
pip install -r requirements.txt
uvicorn server.main:app --reload
```

Visit http://localhost:8000/docs to test all endpoints.

## Render Deployment

### Step 1: Prepare Code
```bash
git add .
git commit -m "Add Nipharma FastAPI backend"
git push origin main
```

### Step 2: Create Render Account
1. Go to https://render.com
2. Sign up with GitHub account
3. Create new Web Service

### Step 3: Configure Service
1. **Name**: `nipharma-backend`
2. **Region**: Choose closest to users
3. **Branch**: `main`
4. **Build Command**: `pip install -r requirements.txt`
5. **Start Command**: `uvicorn server.main:app --host 0.0.0.0 --port 8000`

### Step 4: Add Environment Variables
In Render dashboard:
```
GROQ_API_KEY=<your-groq-api-key>
NEWS_API_KEY=<your-news-api-key>
PYTHONUNBUFFERED=true
```

### Step 5: Deploy
Click "Deploy" button. Service will be live in 2-5 minutes.

## Heroku Deployment

### Step 1: Install Heroku CLI
```bash
brew tap heroku/brew && brew install heroku
heroku login
```

### Step 2: Create Heroku App
```bash
heroku create nipharma-backend
# or with custom domain
heroku create my-custom-app-name
```

### Step 3: Add Environment Variables
```bash
heroku config:set GROQ_API_KEY=<your-groq-api-key>
heroku config:set NEWS_API_KEY=<your-news-api-key>
heroku config:set PYTHONUNBUFFERED=true
```

### Step 4: Deploy
```bash
git push heroku main
```

### Step 5: Monitor
```bash
heroku logs --tail
heroku open
```

## Railway Deployment

### Step 1: Connect Repository
1. Go to https://railway.app
2. Create new project
3. Select "Deploy from GitHub repo"
4. Choose nipharma-backend repository

### Step 2: Add Environment Variables
In Railway dashboard:
```
GROQ_API_KEY=<your-groq-api-key>
NEWS_API_KEY=<your-news-api-key>
```

### Step 3: Configure Service
Railway auto-detects FastAPI. Set:
- **Port**: 8000
- **Start Command**: `uvicorn server.main:app --host 0.0.0.0 --port 8000`

### Step 4: Deploy
Railway auto-deploys on push to main.

## Docker Deployment

### Create Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Build and Run Locally
```bash
docker build -t nipharma-backend .
docker run -p 8000:8000 \
  -e GROQ_API_KEY=<your-key> \
  -e NEWS_API_KEY=<your-key> \
  nipharma-backend
```

### Push to Docker Hub
```bash
docker tag nipharma-backend <your-username>/nipharma-backend
docker push <your-username>/nipharma-backend
```

## Environment Variables Reference

| Variable | Description | Required |
|----------|-------------|----------|
| `GROQ_API_KEY` | Groq API key from console.groq.com | Yes |
| `NEWS_API_KEY` | NewsAPI key from newsapi.org | Yes |
| `HOST` | Server host (default: 0.0.0.0) | No |
| `PORT` | Server port (default: 8000) | No |
| `PYTHONUNBUFFERED` | Set to `true` for real-time logs | No |

## Post-Deployment Verification

### Test Health Endpoint
```bash
curl https://your-deployed-url.com/
```

Expected response:
```json
{
  "status": "running",
  "version": "1.0.0",
  "groq_configured": true,
  "news_api_configured": true
}
```

### Test Chat Endpoint
```bash
curl -X POST https://your-deployed-url.com/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the UK pharmaceutical supply chain?", "chat_history": []}'
```

### Test News Endpoint
```bash
curl https://your-deployed-url.com/news?limit=5
```

### Access API Documentation
Visit: `https://your-deployed-url.com/docs`

## Monitoring and Logs

### Render
1. Go to Dashboard → Service → Logs
2. View real-time logs
3. Check build logs for deployment issues

### Heroku
```bash
heroku logs --tail        # Real-time logs
heroku logs --num=50      # Last 50 lines
heroku logs --ps web      # Only web dyno logs
```

## Troubleshooting

### Issue: 500 Internal Server Error
1. Check environment variables are set correctly
2. Verify API keys are valid
3. Check logs for specific error messages

### Issue: API Keys Not Working
1. Regenerate API keys on Groq and NewsAPI
2. Update environment variables
3. Restart application

### Issue: Slow Response Times
1. Check Groq API quota
2. Consider caching news responses
3. Monitor API rate limits

### Issue: Build Failures
1. Ensure all dependencies in requirements.txt
2. Check Python version (3.8+)
3. Verify no local .env secrets in git

## Scaling Considerations

### For High Traffic
1. Add caching layer (Redis)
2. Implement rate limiting
3. Use load balancer
4. Optimize News API queries

### Cost Optimization
1. Cache news articles for 1 hour
2. Limit chat history retention
3. Use API credits wisely

## Security Checklist

- [ ] Never commit `.env` files
- [ ] Use strong API keys
- [ ] Enable HTTPS (auto on Render/Heroku)
- [ ] Add authentication if needed
- [ ] Rate limit endpoints
- [ ] Monitor for unusual activity
- [ ] Keep dependencies updated

## Update Deployment

### Render
Push to GitHub → Auto-redeploys

### Heroku
```bash
git push heroku main
```

### Docker
```bash
docker build -t nipharma-backend .
docker push <your-username>/nipharma-backend
# Update deployment to use new image
```

## Support & Resources

- Groq API Docs: https://console.groq.com/docs
- NewsAPI Docs: https://newsapi.org/docs
- FastAPI Docs: https://fastapi.tiangolo.com/
- Render Docs: https://render.com/docs
- Heroku Docs: https://devcenter.heroku.com/
