# PRISM Quick Start Guide

Get PRISM up and running in 5 minutes!

## Prerequisites Check

```bash
# Check Python version (need 3.11+)
python --version

# Check Node.js (need 18+)
node --version

# Check pnpm (need 8+)
pnpm --version

# Check Docker
docker --version
docker-compose --version
```

If missing:
- **Python**: Download from [python.org](https://www.python.org/downloads/)
- **Node.js**: Download from [nodejs.org](https://nodejs.org/)
- **pnpm**: `npm install -g pnpm`
- **Docker**: Download from [docker.com](https://www.docker.com/products/docker-desktop/)

## Step-by-Step Setup

### 1. Clone & Navigate
```bash
git clone <your-repo-url>
cd PRISM
```

### 2. Backend Setup (Terminal 1)

```bash
# Create virtual environment
python -m venv prism-venv

# Activate it
source prism-venv/bin/activate  # Mac/Linux
# OR
prism-venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements-dev.txt

# Create .env file
cp .env.example .env

# Edit .env and add your Groq API key
# Get free key from: https://console.groq.com
# Add this line: GROQ_API_KEY=your_actual_key_here
```

### 3. Start Database Services (Terminal 1)

```bash
# Start PostgreSQL & Redis
docker-compose up -d db redis

# Wait 10 seconds for services to start
sleep 10
```

### 4. Start Backend API (Terminal 1)

```bash
# Run the API
uvicorn backend.apps.api.src.main:app --reload --host 0.0.0.0 --port 8000

# API will be at: http://localhost:8000
# Docs at: http://localhost:8000/docs
```

### 5. Start Frontend (Terminal 2)

```bash
# Navigate to frontend
cd frontend/apps/web

# Install dependencies
pnpm install

# Create .env.local
cp .env.example .env.local

# Start dev server
pnpm dev

# Frontend will be at: http://localhost:3000
```

## Verify It's Working

### Backend Check
Open http://localhost:8000/docs
- You should see the API documentation

### Frontend Check
Open http://localhost:3000
- You should see the PRISM interface with Matrix theme

## First Steps

### 1. Create a Session
- Go to "Sessions" in sidebar
- Click "New Session"
- Name it "Test Session"
- Click "Create"

### 2. Upload a Paper
- Go to "Documents" in sidebar
- Drag and drop a PDF file (or click to browse)
- Wait for processing (green checkmark when done)

### 3. Ask Questions
- Go to "Chat" (home page)
- Type a question about your paper
- Example: "What is the main contribution of this paper?"
- Press Enter and wait for response

## Troubleshooting

### Error: "GROQ_API_KEY not set"
```bash
# Edit .env file
nano .env  # or use your text editor

# Add this line:
GROQ_API_KEY=your_actual_groq_key_here

# Save and restart backend
```

### Error: "Port 8000 already in use"
```bash
# Kill process on port 8000
lsof -ti:8000 | xargs kill -9

# Or run on different port
uvicorn backend.apps.api.src.main:app --reload --port 8001
```

### Error: "Port 3000 already in use"
```bash
# Kill process on port 3000
lsof -ti:3000 | xargs kill -9

# Or run on different port
pnpm dev -- -p 3001
```

### Error: "Connection to database failed"
```bash
# Check Docker services
docker-compose ps

# Restart services
docker-compose restart db redis

# Or start fresh
docker-compose down
docker-compose up -d db redis
```

### Error: Frontend can't reach backend
```bash
# Check .env.local in frontend/apps/web/
# Should contain:
NEXT_PUBLIC_API_URL=http://localhost:8000

# Restart frontend after changing
```

## Using Makefile (Alternative)

PRISM includes a Makefile for easier commands:

```bash
# Setup environment
make setup-env

# Install dependencies
make install-dev

# Start database services
make dev-services

# Start API (in new terminal)
make dev-api

# Frontend needs manual start:
cd frontend/apps/web && pnpm dev
```

## Stop Everything

```bash
# Stop frontend: Ctrl+C in Terminal 2

# Stop backend: Ctrl+C in Terminal 1

# Stop Docker services:
docker-compose down
```

## Next Steps

- Read the main [README.md](README.md) for detailed documentation
- Check [frontend/apps/web/README.md](frontend/apps/web/README.md) for frontend details
- See [FRONTEND_COMPLETE.md](FRONTEND_COMPLETE.md) for UI features
- Review [API Documentation](http://localhost:8000/docs) when running

## Support

- **Backend Issues**: Check backend logs in Terminal 1
- **Frontend Issues**: Check browser console (F12)
- **Docker Issues**: Run `docker-compose logs`
- **General Help**: See README.md troubleshooting section

## Success!

You should now have:
- ✓ Backend API running at http://localhost:8000
- ✓ Frontend UI running at http://localhost:3000
- ✓ PostgreSQL and Redis running via Docker
- ✓ FAISS vector store initialized
- ✓ Ability to upload PDFs and ask questions

Happy researching! 🚀
