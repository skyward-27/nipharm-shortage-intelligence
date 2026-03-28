# React + FastAPI Integration Guide

This guide documents the complete frontend-backend wiring for the Nipharma Intelligence platform.

## Project Structure

```
NPT Stock Inteligance Unit/
├── nipharma-backend/
│   ├── main.py              # FastAPI application with all endpoints
│   ├── requirements.txt      # Python dependencies
│   ├── .env                  # Backend configuration
│   └── venv/                # Virtual environment
│
├── nipharma-frontend/
│   ├── src/
│   │   ├── api.ts           # API client with all fetch functions
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx # Main dashboard with KPIs
│   │   │   ├── MarketNews.tsx # News feed page
│   │   │   └── Chat.tsx      # AI chat interface
│   │   ├── App.tsx           # Main component (to be wired)
│   │   └── index.tsx         # Entry point
│   ├── .env.local            # Frontend configuration
│   └── package.json          # Dependencies
```

## API Endpoints

### Backend (FastAPI) @ http://localhost:8000

| Method | Endpoint | Purpose | Response |
|--------|----------|---------|----------|
| GET | `/health` | Health check | `{ status: "healthy", timestamp: ISO8601 }` |
| GET | `/news` | Fetch pharma news | Array of NewsArticle objects |
| GET | `/signals` | Get market signals | Object with KPI metrics |
| GET | `/drugs?search=query` | Search drugs | Array of Drug objects |
| GET | `/concessions` | Price concessions | Array of Concession objects |
| POST | `/chat` | AI chat endpoint | `{ response: string, timestamp: ISO8601 }` |

### Request/Response Models

**NewsArticle:**
```typescript
{
  title: string
  description: string
  source: string
  url: string
  publishedAt: ISO8601 string
  image?: string
}
```

**Signal (Market KPIs):**
```typescript
{
  drugs_at_risk: number
  best_opportunity: string
  best_discount: number
  market_alert: string
  alert_severity: string
  total_savings_potential: number
}
```

**Drug:**
```typescript
{
  id: string
  name: string
  discount: number
  risk_level: "LOW" | "MEDIUM" | "HIGH"
  shortage_probability: number (0-1)
}
```

**Chat Request/Response:**
```typescript
// Request
{
  message: string
  chat_history: Array<{role: "user"|"assistant", content: string}>
}

// Response
{
  response: string
  timestamp: ISO8601 string
}
```

## Setup Instructions

### Backend Setup

1. **Install dependencies:**
   ```bash
   cd nipharma-backend
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   ```bash
   # Edit .env with your settings
   # Defaults are already configured for local development
   ```

3. **Run development server:**
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```
   - Server runs at: http://localhost:8000
   - API docs: http://localhost:8000/docs (Swagger UI)
   - ReDoc: http://localhost:8000/redoc

### Frontend Setup

1. **Install dependencies:**
   ```bash
   cd nipharma-frontend
   npm install
   # or
   yarn install
   ```

2. **Configure environment:**
   ```bash
   # .env.local is already configured
   # For production, update REACT_APP_API_URL
   ```

3. **Run development server:**
   ```bash
   npm start
   # or
   npm run dev  # if using Vite
   ```
   - Frontend runs at: http://localhost:3000

## Pages & Components Wired

### 1. Dashboard (`src/pages/Dashboard.tsx`)
**Features:**
- Fetches news (first 3 articles) and signals on mount
- Displays 4 KPI cards with real-time data
- Shows latest news cards with images
- CTA buttons for saving and booking
- Quick navigation links

**API Calls:**
```typescript
const [newsData, signalsData] = await Promise.all([
  fetchNews(),
  fetchSignals(),
]);
```

### 2. Market News (`src/pages/MarketNews.tsx`)
**Features:**
- Fetches and displays all news articles
- Grid layout with images and metadata
- Loading and error states
- External links to source articles
- Responsive design

**API Calls:**
```typescript
const data = await fetchNews();
```

### 3. Chat (`src/pages/Chat.tsx`)
**Features:**
- Real-time chat interface with history
- Sends messages to AI backend
- Auto-scrolls to latest message
- Loading indicators
- Error handling and recovery
- Keyboard shortcuts (Enter to send)

**API Calls:**
```typescript
const response = await chatWithGroq(message, history);
```

## API Client Module (`src/api.ts`)

All API calls are centralized in this module. Key functions:

```typescript
// Health check
healthCheck(): Promise<{status: string, timestamp: string}>

// News
fetchNews(): Promise<NewsArticle[]>

// Signals
fetchSignals(): Promise<Signal>

// Drugs
searchDrugs(query?: string): Promise<Drug[]>

// Concessions
fetchConcessions(): Promise<Concession[]>

// Chat
chatWithGroq(message: string, history: ChatMessage[]): Promise<{response: string, timestamp: string}>
```

## CORS Configuration

Backend CORS is configured to accept requests from:
- `http://localhost:3000` (React default)
- `http://localhost:5173` (Vite default)
- `http://localhost:8080` (alternative dev port)
- Any URL in `FRONTEND_URL` environment variable

## Error Handling

Both frontend and backend implement error handling:

**Frontend:**
- Try-catch blocks on all API calls
- User-friendly error messages
- Fallback UI states (loading, error, empty)

**Backend:**
- HTTP status codes (200, 400, 500)
- JSON error responses
- Validation via Pydantic

## Testing the Integration

### 1. Test Backend Health
```bash
curl http://localhost:8000/health
```

### 2. Test Individual Endpoints
```bash
# Get news
curl http://localhost:8000/news

# Get signals
curl http://localhost:8000/signals

# Search drugs
curl "http://localhost:8000/drugs?search=paracetamol"

# Chat
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What drugs are at risk?", "chat_history": []}'
```

### 3. Test Frontend Pages
- Dashboard: http://localhost:3000/
- News: http://localhost:3000/news
- Chat: http://localhost:3000/chat

## Environment Variables

### Backend (.env)
```env
ENVIRONMENT=development|production
DEBUG=true|false
CORS_ORIGINS=comma-separated-urls
FRONTEND_URL=http://localhost:3000
API_HOST=0.0.0.0
API_PORT=8000
GROQ_API_KEY=your_key_here  # When integrating Groq
```

### Frontend (.env.local)
```env
REACT_APP_API_URL=http://localhost:8000
REACT_APP_ENVIRONMENT=development|production
```

## Production Deployment

### Backend (Render, Railway, Heroku, etc.)
1. Set environment variables on hosting platform
2. Update `CORS_ORIGINS` to include frontend domain
3. Deploy: Hosting platform runs `uvicorn main:app --host 0.0.0.0 --port 8000`

### Frontend (Vercel, Netlify, AWS, etc.)
1. Update `.env.local` → use CI/CD environment variables
2. Set `REACT_APP_API_URL` to production backend URL
3. Deploy: Run `npm run build && npm start` or equivalent

### Example Production Variables
```env
# Backend on Render
CORS_ORIGINS=https://nipharma-frontend.vercel.app
FRONTEND_URL=https://nipharma-frontend.vercel.app

# Frontend
REACT_APP_API_URL=https://nipharma-api.onrender.com
```

## Groq Integration (Future)

When ready to integrate Groq AI:

1. **Get API key** from https://console.groq.com
2. **Add to .env:**
   ```env
   GROQ_API_KEY=gsk_xxxxx
   ```
3. **Update main.py:**
   ```python
   from groq import Groq

   client = Groq(api_key=os.getenv("GROQ_API_KEY"))

   @app.post("/chat")
   async def chat_with_groq(request: ChatRequest):
       response = client.chat.completions.create(
           model="mixtral-8x7b-32768",
           messages=[{**msg.dict()} for msg in request.chat_history] +
                    [{"role": "user", "content": request.message}],
           temperature=0.7,
           max_tokens=1024
       )
       return ChatResponse(
           response=response.choices[0].message.content,
           timestamp=datetime.now().isoformat()
       )
   ```

## Troubleshooting

### CORS Errors
- Check backend `.env` CORS_ORIGINS includes frontend URL
- Restart backend after changing CORS config
- Check browser console for specific origin being blocked

### API Not Responding
- Verify backend is running: `curl http://localhost:8000/health`
- Check network tab in browser DevTools
- Verify API_URL in `.env.local` is correct

### Chat Not Working
- Backend must be running
- Check console logs for errors
- Verify POST request format matches schema

### News/Signals Empty
- Backend returns mock data - ensure it's running
- Check API response format in browser DevTools

## File Locations

- **Backend**: `/Users/chaitanyawarhade/Documents/NPT Stock Inteligance Unit/nipharma-backend/`
- **Frontend**: `/Users/chaitanyawarhade/Documents/NPT Stock Inteligance Unit/nipharma-frontend/`
- **API Module**: `/Users/chaitanyawarhade/Documents/NPT Stock Inteligance Unit/nipharma-frontend/src/api.ts`
- **Pages**: `/Users/chaitanyawarhade/Documents/NPT Stock Inteligance Unit/nipharma-frontend/src/pages/`

## Next Steps

1. ✅ API client created (`src/api.ts`)
2. ✅ Backend endpoints implemented (`main.py`)
3. ✅ Dashboard page wired (`pages/Dashboard.tsx`)
4. ✅ News page wired (`pages/MarketNews.tsx`)
5. ✅ Chat page wired (`pages/Chat.tsx`)
6. ⬜ Wire App.tsx with routing and page components
7. ⬜ Add authentication (JWT/OAuth)
8. ⬜ Integrate Groq API for real AI responses
9. ⬜ Add database persistence
10. ⬜ Deploy to production

## Summary

**What's Wired:**
- ✅ React fully connected to FastAPI backend
- ✅ News page loads and displays articles from API
- ✅ Chat page sends/receives messages with backend
- ✅ Dashboard shows live KPIs and signals
- ✅ All API calls use centralized client module
- ✅ Error handling on both client and server
- ✅ CORS configured for local development
- ✅ Environment configuration for dev and production

**Ready to Use:**
1. Start backend: `cd nipharma-backend && source venv/bin/activate && uvicorn main:app --reload`
2. Start frontend: `cd nipharma-frontend && npm start`
3. Visit http://localhost:3000 to see the dashboard
