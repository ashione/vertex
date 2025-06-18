# Vertex

A powerful tool for local and cloud-based LLM inference and workflow orchestration, featuring an intuitive Web interface and advanced VertexFlow engine.

## Features

- **Multi-Model Support**: Ollama local models and external APIs (DeepSeek, OpenRouter)
- **Web Chat Interface**: Real-time streaming conversations with multi-turn context
- **VertexFlow Engine**: Visual workflow orchestration with drag-and-drop nodes
- **RAG System**: Local Retrieval-Augmented Generation with document processing
- **Function Tools**: Custom function registration for dynamic workflows
- **Document Processing**: Support for TXT, MD, PDF, DOCX formats

## Quick Start

### Requirements
- Python 3.8+
- Ollama (for local models) - [Download here](https://ollama.com/download)

### Installation
```bash
# Clone repository
git clone git@github.com:ashione/vertex.git
cd vertex

# Install dependencies
uv pip install -r requirements.txt
uv pip install -e .

# Setup local model (optional)
python scripts/setup_ollama.py

# Install RAG dependencies
./scripts/install_rag_deps.sh
```

### Launch
```bash
# Standard mode
vertex

# VertexFlow workflow mode
python -m vertex_flow.src.app
```

Access the Web interface at [http://localhost:7860](http://localhost:7860)

## Usage

### Web Interface
- **Chat**: Multi-turn conversations with streaming output
- **Workflow Editor**: Visual workflow design at [http://localhost:7860/workflow](http://localhost:7860/workflow)
- **Configuration**: API keys and model parameters

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

Set API keys for external models:
```bash
export llm_deepseek_sk="your-key"
export llm_openrouter_sk="your-key"
```

## Documentation

- [RAG System](vertex_flow/docs/RAG_README.md)
- [Document Update](vertex_flow/docs/DOCUMENT_UPDATE.md)
- [Deduplication](vertex_flow/docs/DEDUPLICATION.md)
- [Workflow Components](vertex_flow/docs/)

## Examples

```bash
# Run RAG example
cd vertex_flow/examples
python rag_example.py

# Run deduplication demo
python deduplication_demo.py
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
