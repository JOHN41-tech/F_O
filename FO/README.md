# AI Learning Assistant

A fully functional AI-powered learning assistant with interactive features.

## Project Structure

```
AI AGENT/
├── backend/                 # Backend code
│   ├── api/                # API integrations
│   │   └── perplexity.py  # Perplexity API client
│   ├── core/               # Core business logic
│   │   ├── roadmap.py     # Roadmap parsing
│   │   └── session.py     # Session management
│   └── utils/              # Utilities
│       ├── database.py    # Database operations
│       └── quiz_generator.py  # Quiz generation
│
├── frontend/               # Frontend code
│   ├── static/            # Static assets
│   │   ├── style.css     # Styles
│   │   └── script.js     # JavaScript
│   └── templates/         # HTML templates
│       └── index.html    # Main page
│
├── app.py                 # Flask application entry point
├── Dockerfile             # Docker configuration
├── docker-compose.yml     # Docker Compose configuration
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables (API keys)
├── .env.example          # Environment template
├── .dockerignore         # Docker ignore rules
├── .gitignore            # Git ignore rules
└── venv/                 # Virtual environment
```

## Features

- 💬 Interactive AI chat
- 📝 Auto-generated quizzes
- 📌 Note-taking system
- 📊 Progress tracking
- 🗄️ SQLite database persistence
- 🎨 Dark theme UI

## Local Development

### Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure API key:**
   - Copy `.env.example` to `.env`
   - Add your Perplexity API key:
     ```
     PERPLEXITY_API_KEY=your_key_here
     ```

3. **Run the application:**
   ```bash
   python app.py
   ```

4. **Open browser:**
   Navigate to http://localhost:5000

## Docker Deployment

### Using Docker Compose (Recommended)

1. **Set environment variables:**
   ```bash
   export PERPLEXITY_API_KEY=your_key_here
   ```

2. **Build and run:**
   ```bash
   docker-compose up -d
   ```

3. **Access the application:**
   Navigate to http://localhost:5000

4. **Stop the application:**
   ```bash
   docker-compose down
   ```

### Using Docker directly

1. **Build the image:**
   ```bash
   docker build -t ai-learning-assistant .
   ```

2. **Run the container:**
   ```bash
   docker run -d \
     -p 5000:5000 \
     -e PERPLEXITY_API_KEY=your_key_here \
     -v $(pwd)/learning_assistant.db:/app/learning_assistant.db \
     --name ai-learning-assistant \
     ai-learning-assistant
   ```

3. **View logs:**
   ```bash
   docker logs -f ai-learning-assistant
   ```

4. **Stop the container:**
   ```bash
   docker stop ai-learning-assistant
   docker rm ai-learning-assistant
   ```

## Environment Variables

- `PERPLEXITY_API_KEY` - Your Perplexity API key (required)
- `PORT` - Port to run the application (default: 5000)
- `HOST` - Host to bind to (default: 0.0.0.0)
- `FLASK_ENV` - Environment mode: development/production (default: development)
- `SECRET_KEY` - Flask secret key for sessions (auto-generated if not set)

## Deployment to Cloud

### Deploy to Railway/Render/Fly.io

1. Push code to GitHub
2. Connect repository to platform
3. Set environment variable: `PERPLEXITY_API_KEY`
4. Deploy!

### Deploy to AWS/GCP/Azure

1. Build Docker image
2. Push to container registry
3. Deploy to container service (ECS, Cloud Run, Container Apps)
4. Set environment variables
5. Configure load balancer/ingress

## Technologies

- **Backend:** Flask, SQLite, Python
- **Frontend:** HTML, CSS, JavaScript
- **AI:** Perplexity API
- **Deployment:** Docker, Docker Compose

## License

MIT
