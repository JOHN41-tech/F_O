# Deployment Guide

## Quick Start with Docker

### Prerequisites
- Docker installed
- Docker Compose installed (optional, but recommended)
- Perplexity API key

### Option 1: Docker Compose (Easiest)

1. **Set your API key:**
   ```bash
   # On Windows PowerShell
   $env:PERPLEXITY_API_KEY="your_api_key_here"
   
   # On Linux/Mac
   export PERPLEXITY_API_KEY="your_api_key_here"
   ```

2. **Build and run:**
   ```bash
   docker-compose up -d
   ```

3. **Access the app:**
   Open http://localhost:5000

4. **View logs:**
   ```bash
   docker-compose logs -f
   ```

5. **Stop the app:**
   ```bash
   docker-compose down
   ```

### Option 2: Docker CLI

1. **Build the image:**
   ```bash
   docker build -t ai-learning-assistant .
   ```

2. **Run the container:**
   ```bash
   docker run -d \
     -p 5000:5000 \
     -e PERPLEXITY_API_KEY=your_key_here \
     -v ${PWD}/learning_assistant.db:/app/learning_assistant.db \
     --name ai-learning-assistant \
     ai-learning-assistant
   ```

3. **Access the app:**
   Open http://localhost:5000

## Cloud Deployment

### Deploy to Railway

1. Install Railway CLI:
   ```bash
   npm install -g @railway/cli
   ```

2. Login and deploy:
   ```bash
   railway login
   railway init
   railway up
   ```

3. Set environment variable:
   ```bash
   railway variables set PERPLEXITY_API_KEY=your_key_here
   ```

### Deploy to Render

1. Push code to GitHub
2. Go to https://render.com
3. Create new Web Service
4. Connect your GitHub repository
5. Set environment variables:
   - `PERPLEXITY_API_KEY`: your_key_here
6. Deploy!

### Deploy to Fly.io

1. Install Fly CLI:
   ```bash
   curl -L https://fly.io/install.sh | sh
   ```

2. Login and launch:
   ```bash
   fly auth login
   fly launch
   ```

3. Set secrets:
   ```bash
   fly secrets set PERPLEXITY_API_KEY=your_key_here
   ```

4. Deploy:
   ```bash
   fly deploy
   ```

### Deploy to AWS (ECS)

1. Build and push to ECR:
   ```bash
   aws ecr create-repository --repository-name ai-learning-assistant
   docker tag ai-learning-assistant:latest <account-id>.dkr.ecr.<region>.amazonaws.com/ai-learning-assistant:latest
   docker push <account-id>.dkr.ecr.<region>.amazonaws.com/ai-learning-assistant:latest
   ```

2. Create ECS task definition with environment variable
3. Create ECS service
4. Configure load balancer

### Deploy to Google Cloud Run

1. Build and push to GCR:
   ```bash
   gcloud builds submit --tag gcr.io/<project-id>/ai-learning-assistant
   ```

2. Deploy:
   ```bash
   gcloud run deploy ai-learning-assistant \
     --image gcr.io/<project-id>/ai-learning-assistant \
     --platform managed \
     --set-env-vars PERPLEXITY_API_KEY=your_key_here \
     --allow-unauthenticated
   ```

## Environment Variables

Required:
- `PERPLEXITY_API_KEY` - Your Perplexity API key

Optional:
- `PORT` - Port (default: 5000)
- `HOST` - Host (default: 0.0.0.0)
- `FLASK_ENV` - Environment (default: development)
- `SECRET_KEY` - Session secret (auto-generated if not set)

## Database Persistence

The SQLite database (`learning_assistant.db`) stores:
- Learning topics and roadmaps
- Progress tracking
- Notes
- Chat history
- Quiz results

**Important:** Mount this file as a volume to persist data across container restarts.

## Troubleshooting

### Container won't start
- Check logs: `docker logs ai-learning-assistant`
- Verify API key is set correctly
- Ensure port 5000 is not in use

### Database issues
- Ensure volume is mounted correctly
- Check file permissions
- Verify database file exists

### API errors
- Verify Perplexity API key is valid
- Check API rate limits
- Review application logs
