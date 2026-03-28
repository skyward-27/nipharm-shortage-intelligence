# Nipharma Backend

FastAPI backend for the Nipharma Stock Intelligence Unit, featuring AI-powered chatbot integration with Groq and pharmaceutical news aggregation.

## Features

- **AI Chatbot**: Powered by Groq's Mixtral-8x7b model for pharmaceutical domain expertise
- **News Integration**: Aggregates pharmaceutical and supply chain news from NewsAPI
- **CORS Enabled**: Ready for frontend integration
- **RESTful API**: Well-documented endpoints with Pydantic validation
- **Production Ready**: Configured for deployment on Render, Heroku, or other platforms

## Project Structure

```
nipharma-backend/
├── server/
│   ├── main.py           # FastAPI application and route definitions
│   ├── chat.py           # Groq chatbot integration
│   ├── news.py           # News API integration
│   └── __init__.py       # Package initialization
├── requirements.txt      # Python dependencies
├── Procfile              # Deployment configuration
├── .env.example          # Environment variables template
└── README.md             # This file
```

## Setup Instructions

### Prerequisites

- Python 3.8+
- pip or poetry
- Groq API key (https://console.groq.com/keys)
- NewsAPI key (https://newsapi.org/)

### Local Development

1. **Clone the repository and navigate to the directory:**
   ```bash
   cd "/Users/chaitanyawarhade/Documents/NPT Stock Inteligance Unit/nipharma-backend"
   ```

2. **Create and activate virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Setup environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env and add your API keys
   ```

5. **Run the development server:**
   ```bash
   uvicorn server.main:app --reload
   ```

   The API will be available at `http://localhost:8000`

6. **Access API documentation:**
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

## API Endpoints

### Health Check
- **GET** `/` - Health check and configuration status

### Chat Endpoints
- **POST** `/chat` - Chat with Nipharma AI assistant
  - Request body: `{"message": "string", "chat_history": []}`
  - Response: `{"response": "string", "role": "assistant"}`

### News Endpoints
- **GET** `/news?limit=10` - Get latest pharmaceutical news
- **GET** `/news/supply-chain?limit=10` - Get supply chain news
- **GET** `/news/search?query=&limit=10` - Search for specific news

### Placeholder Endpoints (Coming Soon)
- **GET** `/drugs?search=` - Search pharmaceutical drugs database
- **GET** `/concessions` - Get concession trends
- **GET** `/signals` - Get market signals (GBP/INR, Brent crude, BoE rate)
- **GET** `/early-warnings` - Get supply chain disruption warnings

## Example Requests

### Chat Example
```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What are the current drug shortages in the UK?",
    "chat_history": []
  }'
```

### News Example
```bash
curl "http://localhost:8000/news?limit=5"
```

### News Search Example
```bash
curl "http://localhost:8000/news/search?query=drug%20shortage&limit=10"
```

## Environment Variables

Create a `.env` file in the root directory with the following variables:

```env
# Groq API Configuration
GROQ_API_KEY=your_groq_api_key_here

# News API Configuration
NEWS_API_KEY=your_news_api_key_here

# Server Configuration (optional)
HOST=0.0.0.0
PORT=8000
ENVIRONMENT=development
```

## Deployment

### Deploy to Render

1. Push code to GitHub
2. Create new Web Service on Render
3. Connect your GitHub repository
4. Set environment variables (GROQ_API_KEY, NEWS_API_KEY)
5. Render will automatically use the Procfile
6. Service will be available at your Render URL

### Deploy to Heroku

1. Install Heroku CLI
2. Login to Heroku: `heroku login`
3. Create app: `heroku create nipharma-backend`
4. Add environment variables:
   ```bash
   heroku config:set GROQ_API_KEY=your_key
   heroku config:set NEWS_API_KEY=your_key
   ```
5. Deploy: `git push heroku main`

## Dependencies

- **fastapi**: Modern web framework
- **uvicorn**: ASGI server
- **groq**: Groq API client
- **requests**: HTTP library for News API
- **python-dotenv**: Environment variable management
- **pydantic**: Data validation

## Error Handling

The API includes comprehensive error handling:
- Missing API keys return informative error messages
- Network timeouts are handled gracefully
- Invalid requests return HTTP 400 with details
- Server errors return HTTP 500 with error message

## Performance Considerations

- News API requests have a 10-second timeout
- Chat responses use temperature=0.7 for balanced creativity/consistency
- Maximum token limit set to 512 for chat responses
- News queries are limited to the 10 most recent articles by default

## Future Enhancements

1. Database integration for persistent chat history
2. Authentication and user accounts
3. Caching for news articles and frequently asked questions
4. Real-time market signals (GBP/INR, Brent crude prices, BoE rates)
5. Drug database integration with CSV/Excel data
6. Concession trends analysis
7. Supply chain risk prediction
8. Rate limiting and usage tracking

## Troubleshooting

**Issue**: "GROQ_API_KEY not configured"
- **Solution**: Ensure .env file exists and contains valid GROQ_API_KEY

**Issue**: "NEWS_API_KEY not configured"
- **Solution**: Ensure .env file exists and contains valid NEWS_API_KEY

**Issue**: Chat returns empty response
- **Solution**: Check Groq API quota and ensure your API key is valid

**Issue**: News endpoint returns no articles
- **Solution**: Verify your NewsAPI key is active and you haven't exceeded rate limits

## Contributing

1. Create a feature branch
2. Make your changes
3. Test locally with `uvicorn server.main:app --reload`
4. Commit and push to GitHub
5. Create a pull request

## License

Proprietary - Nipharma Stock Intelligence Unit

## Support

For issues or questions, contact the development team.
