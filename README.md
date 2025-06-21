# Vertex

A powerful local AI workflow system with multi-model support and visual workflow orchestration.

## Features

- **Multi-Model Support**: Ollama local models and external APIs (DeepSeek, OpenRouter, Tongyi)
- **Function Tools**: Built-in command line execution and system integration tools
- **Unified CLI**: Simple command interface with multiple operation modes
- **VertexFlow Engine**: Visual workflow orchestration with drag-and-drop nodes
- **RAG System**: Local Retrieval-Augmented Generation with document processing
- **Smart Configuration**: Template-based config with automatic setup
- **Document Processing**: Support for TXT, MD, PDF, DOCX formats
- **Desktop Application**: Native desktop app with PyWebView integration

## Quick Start

### Requirements
- Python 3.9+
- Ollama (for local models) - [Download here](https://ollama.com/download)

### Installation
```bash
# Install via pip (recommended)
pip install vertex

# Or install from source
git clone https://github.com/ashione/vertex.git
cd vertex
pip install -e .
```

### Configuration
```bash
# Quick setup - Initialize configuration
vertex config init

# Interactive configuration wizard
vertex config

# Check configuration status
vertex config check
```

### Launch
```bash
# Standard chat mode (default)
vertex

# Or explicitly specify mode
vertex run

# Advanced workflow chat with function tools
python vertex_flow/src/workflow_app.py --port 7864

# VertexFlow workflow mode
vertex workflow

# RAG document Q&A mode
vertex rag --interactive

# Desktop mode
vertex --desktop
```

Access the Web interface at [http://localhost:7860](http://localhost:7860) (or [http://localhost:7864](http://localhost:7864) for workflow app)

## Usage Guide

### CLI Commands
```bash
# Standard mode
vertex                    # Launch chat interface
vertex run --port 8080   # Custom port

# Advanced workflow chat mode
python vertex_flow/src/workflow_app.py --port 7864  # With function tools support

# Workflow mode
vertex workflow           # Visual workflow editor
vertex workflow --port 8080

# Configuration management
vertex config             # Interactive setup
vertex config init        # Quick initialization
vertex config check       # Check status
vertex config reset       # Reset to template

# RAG system
vertex rag --interactive  # Interactive Q&A
vertex rag --query "question"  # Direct query
vertex rag --directory /path/to/docs  # Index documents

# Desktop mode
vertex --desktop          # Desktop application
vertex workflow --desktop # Desktop workflow editor
```

### RAG System
```python
from vertex_flow.workflow.unified_rag_workflow import UnifiedRAGSystem

# Create RAG system
rag_system = UnifiedRAGSystem()

# Index documents
documents = ["document1.txt", "document2.pdf"]
rag_system.index_documents(documents)

# Query the knowledge base
answer = rag_system.query("What is the main topic?")
print(answer)
```

### Function Tools
```python
# Access various function tools through service
from vertex_flow.workflow.service import VertexFlowService

service = VertexFlowService()
cmd_tool = service.get_command_line_tool()      # Command execution
web_tool = service.get_web_search_tool()        # Web search
finance_tool = service.get_finance_tool()       # Financial data

# Tools integrate seamlessly with AI workflows
```

### Basic Workflow
```python
from vertex_flow.workflow.vertex.vertex import SourceVertex
from vertex_flow.workflow.workflow import Workflow, WorkflowContext

def source_func(inputs, context):
    return {"text": "Hello, Vertex Flow!"}

context = WorkflowContext()
workflow = Workflow(context)
source = SourceVertex(id="source", task=source_func)
workflow.add_vertex(source)
workflow.execute_workflow()
```

## Configuration

### Quick Setup
After installing the vertex package, use these commands for quick setup:

```bash
# Initialize configuration file
vertex config init

# Interactive configuration wizard
vertex config

# Check configuration status
vertex config check

# Reset configuration
vertex config reset
```

### Manual Configuration
Configuration file is located at `~/.vertex/config/llm.yml`. You can edit this file directly.

### Environment Variables
Set API keys for external models:
```bash
export llm_deepseek_sk="your-deepseek-key"
export llm_openrouter_sk="your-openrouter-key"
export llm_tongyi_sk="your-tongyi-key"
export web_search_bocha_sk="your-bocha-key"
```

### Configuration Priority
1. User configuration file: `~/.vertex/config/llm.yml`
2. Environment variables
3. Package default configuration

## Documentation

### 📖 User Guides
- [Complete CLI Usage Guide](docs/CLI_USAGE.md) - Full CLI command reference
- [Desktop Application Guide](docs/DESKTOP_APP.md) - Desktop app usage
- [RAG CLI Detailed Guide](docs/RAG_CLI_USAGE.md) - RAG Q&A system guide
- [RAG Performance Optimization](docs/RAG_PERFORMANCE_OPTIMIZATION.md) - Performance analysis and tips
- [Troubleshooting Guide](docs/TROUBLESHOOTING.md) - Common issues and solutions

### 🔧 Technical Documentation
- [Function Tools Guide](docs/FUNCTION_TOOLS.md) - Complete function tools reference
- [RAG System Overview](vertex_flow/docs/RAG_README.md) - Retrieval-Augmented Generation
- [Document Update Mechanism](vertex_flow/docs/DOCUMENT_UPDATE.md) - Incremental updates and deduplication
- [Deduplication Features](vertex_flow/docs/DEDUPLICATION.md) - Smart document deduplication
- [Workflow Components](vertex_flow/docs/) - VertexFlow engine components

## Examples

```bash
# Function tools examples
cd vertex_flow/examples
python command_line_example.py   # Command line tool
python web_search_example.py     # Web search tool  
python finance_example.py        # Finance tool

# Other examples
python rag_example.py            # RAG system
python deduplication_demo.py     # Deduplication
```

## Development

```bash
# Run pre-commit checks
./scripts/precommit.sh

# Sanitize config files
python scripts/sanitize_config.py
```

## License

See LICENSE file for details.
