# Nipharma Backend

FastAPI backend for the Nipharma Stock Intelligence Unit, featuring AI-powered chatbot integration with Groq and pharmaceutical news aggregation.

## Features

- **ML Prediction Model (v4)**: Random Forest classifier (AUC 0.9983) predicts NHS drug shortage events before they occur
- **Hybrid Scoring**: 70% ML model predictions + 30% real-time signals (MHRA alerts, market stress, CPE availability)
- **AI Chatbot**: Powered by Groq's llama-3.1-8b-instant for pharmaceutical domain expertise
- **News Integration**: Aggregates pharmaceutical and supply chain news from NewsAPI
- **CORS Enabled**: Ready for frontend integration
- **RESTful API**: Well-documented endpoints with Pydantic validation
- **Production Ready**: Configured for deployment on Railway, Render, Heroku

## ML Model: Drug Shortage Prediction

The backend includes a trained Random Forest model that predicts NHS drug shortage events (concession prices) before they occur.

### Model Specifications
- **Algorithm**: Random Forest Classifier (100 trees, max_depth=15)
- **Training Data**: 44,074 records (758 drugs × 60 months, April 2021–February 2026)
- **Features**: 28 features across 6 categories (pricing, concessions, market signals, demand, shortage indicators)
- **Performance**: ROC-AUC 0.9983 (5-fold stratified cross-validation) — 5 folds: [0.9982, 0.9984, 0.9978, 0.9986, 0.9986]
- **Class Distribution**: 94.9% negative (not on concession), 5.1% positive (on concession) — handled via balanced class weights

### `/predict` Endpoint
- **URL**: `POST /predict`
- **Input**: Drug features (price, concession history, market signals, demand indicators)
- **Processing**: Hybrid scoring approach
  - Model prediction: 70% weight (historical patterns)
  - Real-time signals: 30% weight (MHRA alerts +0.05–0.15, CPE availability +0.20, demand spikes +0.12, price stress +0.05–0.15)
- **Output**: Action tag (BUY NOW ≥0.70, BUFFER 0.50–0.69, MONITOR <0.50), confidence, explanation

### Example Request
```bash
curl -X POST "http://localhost:8000/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "drug_name": "Metformin 1g tablet",
    "price_gbp": 2.45,
    "floor_proximity": 0.92,
    "on_concession": 0,
    "concession_streak": 0,
    "conc_last_6mo": 2,
    "price_mom_pct": -3.2,
    "mhra_mention_count": 1,
    "cpe_conc_available": 1
  }'
```

### Model Retraining
- **Frequency**: Monthly (not daily) — optimal for CPE (Concession & Price Entry) monthly release schedule
- **Why Monthly?**: Invoice data does not predict CPE timing. CPE is published monthly by NHS VPAS. Daily retraining would add noise.
- **Real-Time Updates**: While model retrains monthly, real-time signals (MHRA alerts, Brent crude, FX rates) update daily
- **Result**: Stable predictions + responsive real-time alerts

### Top 10 Features by Importance
1. on_concession (28.2%)
2. concession_streak (24.7%)
3. conc_last_6mo (18.9%)
4. price_mom_pct (13.7%)
5. floor_proximity (5.8%)
6. within_15pct_of_floor (3.2%)
7. mhra_mention_count (2.4%)
8. cpe_conc_available (2.1%)
9. cpe_price_gbp (1.8%)
10. fx_stress_score (1.8%)

### Model File
- **Location**: `nipharma-backend/model/panel_model.pkl` (5.0 MB)
- **Format**: scikit-learn pickle (loaded at server startup)
- **Dependencies**: scikit-learn, numpy, pandas

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

### ML Prediction
- **POST** `/predict` - Predict drug shortage probability (hybrid ML + real-time signals)
  - Request body: Drug features (28 fields: price, concession history, market signals, etc.)
  - Response: `{"drug_name": "string", "model_probability": float, "real_time_signals": float, "final_probability": float, "action": "BUY NOW|BUFFER|MONITOR", "confidence": "HIGH|MEDIUM|LOW", "explanation": "string"}`

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

## Future Enhancements (v5+ Roadmap)

### Model Improvements
1. Add seasonal pattern feature (month × BNF category interaction) — expected +0.5% AUC
2. Add manufacturer count signal (MHRA marketing authorisation database) — expected +0.8% AUC
3. Add prescribing demand trend (NHSBSA PCA demand data) — expected +0.6% AUC
4. Evaluate ensemble approaches (LSTM + XGBoost ensemble) for edge cases

### Backend Features
1. API response caching (6-hour cache for /predict results)
2. Database integration for persistent chat history + prediction audit trail
3. Authentication and user accounts (Resend email verification)
4. Real-time market signals dashboard (GBP/INR, Brent crude, BoE rates)
5. Automated weekly email via Resend.com (Monday briefing to pharmacy staff)
6. Rate limiting and usage tracking per user

### Integration
1. WhatsApp alerts API (send shortage warnings via WhatsApp)
2. PMR (Pharmacy Management System) data ingestion (if available)
3. Performance monitoring per drug (AUC per drug, top 10 misclassified)

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
