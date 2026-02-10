# PRISM Core Package

The main backend package containing all core agentic AI functionality.

## Structure

```
core/
├── agents/          # Agent implementations
│   ├── base/        # Base classes and interfaces
│   └── implementations/  # Concrete agents (ReAct, etc.)
├── llm/             # LLM provider integrations
│   ├── providers/   # OpenAI, Anthropic, local models
│   └── models/      # Model configurations
├── memory/          # Memory management
│   ├── stores/      # Memory storage implementations
│   └── strategies/  # Memory retrieval strategies
├── tools/           # Agent tools
│   ├── builtin/     # Built-in tools
│   └── registry/    # Tool registration and discovery
├── workflows/       # Workflow orchestration
│   └── orchestration/  # Multi-agent workflows
├── vector_store/    # Vector database integrations
│   └── adapters/    # Chroma, Pinecone, etc.
├── monitoring/      # Observability
│   ├── logging/     # Structured logging
│   └── metrics/     # Metrics collection
└── shared/          # Common utilities
    ├── types/       # Type definitions
    ├── utils/       # Helper functions
    └── config/      # Configuration management
```

## Usage

```python
from core.agents import ReactAgent
from core.llm import OpenAIProvider
from core.tools import WebSearchTool

# Create an agent
agent = ReactAgent(
    llm=OpenAIProvider(),
    tools=[WebSearchTool()]
)

# Execute a task
result = await agent.execute("What's the weather today?")
```

## Installation

This package is automatically installed when you install the backend:

```bash
pip install -e ./backend
```

## Development

```bash
# Run tests
pytest backend/packages/core/tests/

# Type checking
mypy backend/packages/core/src/

# Linting
ruff check backend/packages/core/src/
```
