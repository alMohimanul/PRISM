# Development Guide

## Where to Write Code

### Backend Structure

```
backend/
├── packages/         # Reusable libraries (import from multiple apps)
└── apps/            # Applications (runnable services)
```

### When to Create a Package vs Putting Code in App

**Create a package when:**
- Code is reused by multiple apps (api + worker + cli)
- You want to publish/share the code
- It's a complete, isolated feature

**Put code directly in app when:**
- It's specific to that app only
- You're just starting (YAGNI - You Aren't Gonna Need It)
- Tight coupling with app logic

### Current Package Guide

#### 1. `backend/packages/core/`
**Purpose**: Fundamental interfaces and base classes

**Write here:**
- Abstract base classes: `BaseAgent`, `BaseTool`, `BaseMemory`
- Protocol definitions (interfaces)
- Core exceptions: `AgentError`, `ToolExecutionError`
- Type definitions used everywhere

**Example:**
```python
# backend/packages/core/src/interfaces/agent.py
from abc import ABC, abstractmethod

class BaseAgent(ABC):
    @abstractmethod
    async def execute(self, task: str) -> str:
        pass
```

#### 2. `backend/packages/agents/`
**Purpose**: Agent implementations

**Write here:**
- Concrete agent classes: `ReactAgent`, `PlanAndExecuteAgent`
- Agent strategies and planners
- Agent orchestration logic

**Example:**
```python
# backend/packages/agents/src/react_agent.py
from core.interfaces import BaseAgent

class ReactAgent(BaseAgent):
    async def execute(self, task: str) -> str:
        # ReAct loop implementation
        pass
```

#### 3. `backend/packages/llm/`
**Purpose**: LLM provider integrations

**Write here:**
- OpenAI client wrapper
- Anthropic client wrapper
- Local model integrations (Ollama, etc.)
- Embedding generation
- Prompt templates

**Example:**
```python
# backend/packages/llm/src/providers/openai.py
class OpenAIProvider:
    async def complete(self, prompt: str) -> str:
        # Call OpenAI API
        pass
```

#### 4. `backend/packages/memory/`
**Purpose**: Memory and context management

**Write here:**
- Conversation history management
- Context window handling
- Memory retrieval strategies
- Memory summarization

**Example:**
```python
# backend/packages/memory/src/conversation_memory.py
class ConversationMemory:
    def add_message(self, role: str, content: str):
        pass

    def get_context(self, max_tokens: int) -> list:
        pass
```

#### 5. `backend/packages/tools/`
**Purpose**: Agent tools/functions

**Write here:**
- Built-in tools (calculator, web search, etc.)
- Tool registry
- Tool validation
- Custom tool implementations

**Example:**
```python
# backend/packages/tools/src/builtin/web_search.py
class WebSearchTool:
    async def execute(self, query: str) -> str:
        # Search implementation
        pass
```

#### 6. `backend/packages/workflows/`
**Purpose**: Multi-agent workflows

**Write here:**
- Workflow orchestration
- State machines
- Multi-agent coordination
- Workflow persistence

**Example:**
```python
# backend/packages/workflows/src/orchestrator.py
class WorkflowOrchestrator:
    async def run(self, workflow_def: dict):
        # Coordinate multiple agents
        pass
```

#### 7. `backend/packages/vector_store/`
**Purpose**: Vector database integrations

**Write here:**
- ChromaDB adapter
- Pinecone adapter
- Vector search logic
- Embedding storage

**Example:**
```python
# backend/packages/vector_store/src/adapters/chroma.py
class ChromaAdapter:
    def upsert(self, documents: list, embeddings: list):
        pass
```

#### 8. `backend/packages/monitoring/`
**Purpose**: Observability

**Write here:**
- Structured logging
- Metrics collection
- Tracing (OpenTelemetry)
- Performance monitoring

#### 9. `backend/packages/shared/`
**Purpose**: Common utilities

**Write here:**
- Helper functions
- Constants
- Shared types
- Configuration utilities

### Backend Apps

#### `backend/apps/api/`
**Purpose**: REST API server

**Write here:**
- FastAPI routes
- Request/response models (Pydantic)
- Authentication middleware
- API-specific logic

**Example:**
```python
# backend/apps/api/src/main.py
from fastapi import FastAPI
from agents import ReactAgent

app = FastAPI()

@app.post("/chat")
async def chat(message: str):
    agent = ReactAgent()
    return await agent.execute(message)
```

#### `backend/apps/cli/`
**Purpose**: Command-line interface

**Write here:**
- CLI commands
- Interactive prompts
- Development utilities

#### `backend/apps/worker/`
**Purpose**: Background task processing

**Write here:**
- Celery tasks
- Job definitions
- Scheduled tasks

## Recommended Starting Point

### Phase 1: Start Simple
1. Build everything in `backend/apps/api/src/` first
2. Only use `backend/packages/core/` for shared types

### Phase 2: Extract When Needed
When you notice code being duplicated:
1. Extract to appropriate package
2. Import from multiple apps

### Phase 3: Scale
As team grows, maintain package boundaries

## Example Development Flow

**Starting out:**
```python
# backend/apps/api/src/agent.py
class MyAgent:
    pass

# backend/apps/api/src/main.py
from .agent import MyAgent
```

**After you need it in worker too:**
```python
# backend/packages/agents/src/my_agent.py
class MyAgent:
    pass

# backend/apps/api/src/main.py
from agents import MyAgent

# backend/apps/worker/src/tasks.py
from agents import MyAgent
```

## Key Principles

1. **YAGNI**: Don't create abstractions until you need them
2. **DRY**: Extract to packages when you copy-paste
3. **Separation**: Keep business logic in packages, app logic in apps
4. **Testing**: Packages should be independently testable

## Common Mistakes to Avoid

- ❌ Creating packages "just in case"
- ❌ Circular dependencies between packages
- ❌ Putting app-specific code in packages
- ✅ Start in apps, extract to packages when needed
- ✅ Keep packages focused and independent
