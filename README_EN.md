# Vertex

A powerful local AI workflow system with multi-model support and visual workflow orchestration.

## Features

| Category | Feature | Description |
|----------|---------|-------------|
| **AI Models** | Multi-Model Support | Ollama local models and external APIs (DeepSeek, OpenRouter, Tongyi) |
| **Advanced AI** | 🎨 Multimodal Support | Image analysis and text+image conversations with Gemini 2.5 Pro |
| | 🤔 Reasoning Display | AI thinking process visualization (supports DeepSeek R1) |
| | 🔬 Deep Research | Six-stage research workflow with intelligent analysis |
| **Tools & Search** | 🔍 Smart Web Search | Multi-engine support (SerpAPI, DuckDuckGo, Bocha AI, etc.) |
| | Function Tools | Command line execution, web search, financial data tools |
| **Interface** | ⚡ Streaming Output | Real-time AI response display for better interaction |
| | Unified CLI | Simple command interface with multiple operation modes |
| | Desktop Application | Native desktop app with PyWebView integration |
| **Workflow** | VertexFlow Engine | Visual workflow orchestration with drag-and-drop nodes |
| | RAG System | Local Retrieval-Augmented Generation with document processing |
| **Configuration** | Smart Configuration | Simplified configuration system with automatic setup |
| | Document Processing | Support for TXT, MD, PDF, DOCX formats |

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

# Advanced workflow chat with function tools and reasoning
python -m vertex_flow.src.workflow_app --port 7864

# Deep Research analysis tool
vertex deepresearch
# or short form
vertex dr

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
python -m vertex_flow.src.workflow_app --port 7864  # With function tools, web search, reasoning

# Deep Research mode
vertex deepresearch       # Start deep research analysis tool
vertex dr --topic "AI trends"  # Direct research from command line
vertex dr --port 8080     # Custom port for web interface

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

### Deep Research System
The Deep Research tool provides comprehensive analysis through a six-stage workflow:

1. **Topic Analysis** 🔍 - Initial topic understanding and scope definition
2. **Research Planning** 📋 - Strategic research approach and methodology
3. **Information Collection** 📚 - Comprehensive data gathering and source compilation
4. **Deep Analysis** 🔬 - In-depth examination and critical evaluation
5. **Cross Validation** ✅ - Verification and fact-checking across sources
6. **Summary Report** 📄 - Professional research report generation

```python
# Deep Research via API
from vertex_flow.src.deep_research_app import DeepResearchApp

app = DeepResearchApp()
# Configure research parameters and execute
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
web_tool = service.get_web_search_tool()        # Smart web search (SerpAPI/DuckDuckGo/Bocha etc.)
finance_tool = service.get_finance_tool()       # Financial data retrieval

# Tools integrate seamlessly with AI workflows, supporting streaming and reasoning
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
export web_search_serpapi_api_key="your-serpapi-key"
export web_search_bocha_sk="your-bocha-key"
```

### Configuration Priority
1. User configuration file: `~/.vertex/config/llm.yml`
2. Environment variables
3. Package default configuration

## Documentation

### 📖 User Guides
- [Complete CLI Usage Guide](docs/CLI_USAGE.md) - Full CLI command reference and MCP integration
- [Desktop Application Guide](docs/DESKTOP_APP.md) - Desktop app usage
- [Workflow Chat App Guide](docs/WORKFLOW_CHAT_APP.md) - Advanced chat with function tools and reasoning
- [🎨 Multimodal Features Guide](docs/MULTIMODAL_FEATURES.md) - Image analysis and text+image conversations
- [🔍 Web Search Configuration](docs/WEB_SEARCH_CONFIGURATION.md) - Multi-engine search setup
- [MCP Integration Guide](docs/MCP_INTEGRATION.md) - Model Context Protocol support
- [Troubleshooting Guide](docs/TROUBLESHOOTING.md) - Common issues and solutions

### 🔧 Technical Documentation
- [Function Tools Guide](docs/FUNCTION_TOOLS.md) - Complete function tools reference
- [Workflow Chain Calling](docs/WORKFLOW_CHAIN_CALLING.md) - Chain workflow execution
- [RAG System Overview](vertex_flow/docs/RAG_README.md) - Retrieval-Augmented Generation
- [Document Update Mechanism](vertex_flow/docs/DOCUMENT_UPDATE.md) - Incremental updates and deduplication
- [Deduplication Features](vertex_flow/docs/DEDUPLICATION.md) - Smart document deduplication
- [Configuration Unification](docs/CONFIGURATION_UNIFICATION.md) - Unified configuration system

### 🎯 Development & Maintenance
- [Publishing Guide](docs/PUBLISHING.md) - Package publishing and version management
- [Pre-commit Checks](docs/PRECOMMIT_README.md) - Code quality and automated checks

## Examples

```bash
# Function tools examples
cd vertex_flow/examples
python command_line_example.py   # Command line tool
python web_search_example.py     # Web search tool  
python finance_example.py        # Finance tool
python rag_example.py            # RAG system
python deduplication_demo.py     # Deduplication
```

## Development

```bash
# Run pre-commit checks
./scripts/precommit.sh

# Version management
python scripts/version_bump.py
```

## License

See LICENSE file for details.
