# PRISM: Personal Research Intelligence and Synthesis Manager

A multi-agent research assistant system that helps researchers manage papers, compare methodologies, and maintain context across research sessions using RAG (Retrieval-Augmented Generation) and LangGraph agent orchestration.

## Features

- **PDF Ingestion Pipeline**: Upload research papers → Extract text/metadata → Chunk → Embed → Store in zvec
- **Session Management**: Create/load research sessions with context management using Redis
- **RAG-based Literature Review**: Ask questions about papers and get intelligent, context-aware answers
- **LLM-Powered Agent**: LangGraph-orchestrated agent using Groq (Llama 3.1 70B) for natural language understanding
- **REST API**: FastAPI endpoints ready for frontend integration
- **Vector Search**: zvec-powered semantic search over research papers (2x faster than FAISS)

## Tech Stack

- **Backend**: Python 3.11+
- **API Framework**: FastAPI
- **Agent Orchestration**: LangGraph
- **LLM**: Groq (Llama 3.1 70B)
- **Vector Database**: zvec (Alibaba's high-performance in-process vector database)
- **Embeddings**: sentence-transformers (all-MiniLM-L6-v2)
- **Databases**: PostgreSQL (metadata) + Redis (sessions)
- **PDF Processing**: PyMuPDF
- **Frontend**: TypeScript/Next.js (separate implementation)

## Project Structure

```
PRISM/
├── backend/
│   └── apps/
│       └── api/
│           └── src/
│               ├── agents/           # LangGraph agent implementations
│               │   └── literature_reviewer.py
│               ├── services/         # Business logic
│               │   ├── pdf_processor.py
│               │   ├── vector_store.py
│               │   └── session_manager.py
│               ├── models/           # Pydantic models
│               │   ├── request.py
│               │   └── response.py
│               ├── routes/           # API routes
│               │   ├── chat.py
│               │   ├── documents.py
│               │   └── sessions.py
│               ├── config.py         # Configuration
│               └── main.py           # FastAPI app
├── docker-compose.yml                # Docker services
├── pyproject.toml                    # Python dependencies
├── Makefile                          # Development commands
└── .env.example                      # Environment variables template
```

## Quick Start

### Prerequisites

- **Python 3.11+** (for backend)
- **Node.js 18+** and **pnpm 8+** (for frontend)
- **Docker and Docker Compose** (for databases)
- **Groq API key** (get free key from [console.groq.com](https://console.groq.com))

### Backend Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd PRISM
   ```

2. **Set up environment variables**
   ```bash
   make setup-env
   # Edit .env and add your GROQ_API_KEY
   ```

3. **Install Python dependencies**
   ```bash
   python -m venv prism-venv
   source prism-venv/bin/activate  # On Windows: prism-venv\Scripts\activate

   # Option 1: Install from requirements.txt (recommended)
   make install-dev

   # Option 2: Install from pyproject.toml in editable mode
   # make install-editable
   ```

4. **Start required services (PostgreSQL & Redis)**
   ```bash
   make dev-services
   ```

5. **Run the API server**
   ```bash
   make dev-api
   ```

The API will be available at `http://localhost:8000`.

View the interactive API docs at `http://localhost:8000/docs`.

### Frontend Setup

1. **Install frontend dependencies**
   ```bash
   cd frontend/apps/web
   pnpm install
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env.local
   # .env.local should contain:
   # NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

3. **Start the frontend**
   ```bash
   pnpm dev
   # Or from project root: make dev-web
   ```

The frontend will be available at `http://localhost:3000`.

### Full Stack Development

To run both backend and frontend:

```bash
# Terminal 1: Start database services
colima start 

make dev-services

# Terminal 2: Start backend API
make dev-api

# Terminal 3: Start frontend
cd frontend/apps/web && pnpm dev
```

## Usage

### 1. Upload a Research Paper

```bash
curl -X POST "http://localhost:8000/api/documents/upload" \
  -F "file=@paper.pdf"
```

Response:
```json
{
  "document_id": "abc123...",
  "filename": "paper.pdf",
  "page_count": 12,
  "size_bytes": 245678,
  "status": "processed"
}
```

### 2. Create a Research Session

```bash
curl -X POST "http://localhost:8000/api/sessions" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Deep Learning Research",
    "topic": "Transformer architectures"
  }'
```

Response:
```json
{
  "session_id": "xyz789...",
  "name": "Deep Learning Research",
  "topic": "Transformer architectures",
  "created_at": "2024-01-15T10:30:00Z",
  ...
}
```

### 3. Ask Questions About Papers

```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "xyz789...",
    "message": "What is the main contribution of this paper?"
  }'
```

Response:
```json
{
  "session_id": "xyz789...",
  "message": "The main contribution of this paper is...",
  "agent_type": "literature_reviewer",
  "sources": [
    {
      "document_id": "abc123...",
      "text": "Relevant excerpt...",
      "score": 0.85
    }
  ],
  "timestamp": "2024-01-15T10:31:00Z"
}
```

## API Endpoints

### Documents
- `POST /api/documents/upload` - Upload a PDF paper
- `GET /api/documents` - List all uploaded papers
- `GET /api/documents/{document_id}` - Get document metadata
- `DELETE /api/documents/{document_id}` - Delete a document

### Sessions
- `POST /api/sessions` - Create a new research session
- `GET /api/sessions` - List all sessions
- `GET /api/sessions/{session_id}` - Get session details
- `DELETE /api/sessions/{session_id}` - Delete a session
- `POST /api/sessions/{session_id}/documents/{document_id}` - Add document to session

### Chat
- `POST /api/chat` - Send a message and get agent response

### Health
- `GET /` - Root endpoint
- `GET /health` - Health check

## Development Commands

```bash
# Show all available commands
make help

# Code quality
make format       # Format code with black and ruff
make lint         # Run linters
make typecheck    # Run mypy type checking

# Testing
make test         # Run all tests

# Docker
make docker-up    # Start all services (API, DB, Redis)
make docker-down  # Stop all services
make docker-build # Rebuild Docker images

# Clean
make clean        # Remove build artifacts and caches
```

## Configuration

Key environment variables in `.env`:

```bash
# LLM Configuration
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.1-70b-versatile

# Embeddings
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

# Database URLs
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/prism
REDIS_URL=redis://localhost:6379/0

# PDF Processing
MAX_FILE_SIZE_MB=50
CHUNK_SIZE=1000
CHUNK_OVERLAP=200

# zvec Vector Store
VECTOR_INDEX_PATH=./data/zvec_index
```

## Architecture

### PDF Ingestion Pipeline
1. Upload PDF via `/api/documents/upload`
2. Extract text and metadata using PyMuPDF
3. Split text into overlapping chunks (1000 chars with 200 overlap)
4. Generate embeddings using sentence-transformers
5. Store in zvec collection with metadata fields

### RAG Query Flow
1. User sends question via `/api/chat`
2. Literature Reviewer agent retrieves relevant chunks from zvec (top-5)
3. Agent constructs prompt with context and sends to Groq LLM
4. Response is returned with source citations
5. Conversation stored in Redis for session continuity

### Session Management
- Sessions stored in Redis with 24-hour expiration
- Chat history maintained per session
- Document associations tracked per session

## Future Enhancements (Phase 2)

- [ ] **Methodology Comparator Agent**: Extract and compare experimental methodologies across papers
- [ ] **Writing Critic Agent**: Provide feedback on clarity, style, and citations
- [ ] **Agent Router**: Automatically route queries to appropriate specialist agents
- [ ] **WebSocket Support**: Real-time streaming responses
- [ ] **Session Context Pre-loading**: Load relevant papers based on session topic
- [ ] **Advanced PDF Extraction**: Better handling of tables, figures, and equations
- [ ] **Multi-document Q&A**: Answer questions that require synthesizing multiple papers

## Troubleshooting

### Error: "GROQ_API_KEY not set"
Make sure you've created `.env` file and added your Groq API key:
```bash
make setup-env
# Edit .env and add: GROQ_API_KEY=your_actual_key_here
```

### Error: "Connection refused" (Redis/PostgreSQL)
Start the required services:
```bash
make dev-services
```

### Error: "Module not found"
Reinstall dependencies:
```bash
make install-dev
```

### zvec collection corruption
Delete and rebuild the collection:
```bash
rm -rf data/zvec_index
# Re-upload your documents
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License