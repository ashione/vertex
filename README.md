# Vertex

Vertex is a powerful tool for local and cloud-based LLM inference and workflow orchestration, featuring an intuitive Web interface and advanced VertexFlow engine.

## Key Features

### Core Capabilities
- **Local & Cloud Models**: Support for Ollama-based local models (Qwen-7B) and external APIs (DeepSeek, OpenRouter)
- **Web Chat Interface**: Real-time streaming conversations with multi-turn context
- **VertexFlow Engine**: Visual workflow orchestration with multi-model collaboration
- **Knowledge Base**: Vector search, embedding, and reranking capabilities

### Advanced Features
- **Function Tools**: Custom function registration for dynamic workflow invocation
- **Deep Research Workflow**: Automated research with web search, analysis, and structured reporting
- **VertexGroup**: Modular subgraph management with nested organization
- **Dify Compatibility**: Seamless migration from Dify workflow definitions

## Quick Setup

### Requirements
- Python 3.8+
- Ollama (for local models) - [Download here](https://ollama.com/download)

### Installation
```bash
# Clone repository
git clone git@github.com:ashione/vertex.git
cd vertex

# Install dependencies
pip install -r requirements.txt
pip install -e .

# Setup local model (optional)
python scripts/setup_ollama.py
```

### Launch
```bash
# Standard mode
vertex

# VertexFlow workflow mode
python -m vertex_flow.src.app
```

Access the Web interface at [http://localhost:7860](http://localhost:7860)

## Usage Guide

### Web Interface
The Web UI provides three main modules:
- **Chat Interface**: Multi-turn conversations with streaming output and model switching
- **Workflow Editor**: Visual workflow design with drag-and-drop nodes
- **Configuration**: API keys, model parameters, and system settings

### Workflow Editor
Access at [http://localhost:7860/workflow](http://localhost:7860/workflow)

**Available Node Types**:
- **LLM Node**: Text generation with configurable models
- **Retrieval Node**: Knowledge base search
- **Condition Node**: Conditional branching
- **Function Node**: Custom function execution

**Variable System**:
- Environment: `{{#env.variable_name#}}`
- User: `{{user.var.variable_name}}`
- Node Output: `{{node_id.output_field}}`

### Configuration
- Set API keys for external models (DeepSeek, OpenRouter)
- Configure model parameters (temperature, max tokens)
- Automatic sanitization of sensitive information in config files

## Development

### Code Quality
The project includes automated pre-commit checks:
```bash
# Run pre-commit checks
./scripts/precommit.sh

# Sanitize config files
python scripts/sanitize_config.py
```

### Environment Variables
Use environment variables for API keys:
```bash
export llm_deepseek_sk="your-key"
export llm_openrouter_sk="your-key"
```

### Common Issues
- **Ollama connection**: Ensure Ollama is running
- **API errors**: Verify API keys and network connection
- **Workflow issues**: Check browser console for errors

## API Examples

### Basic Workflow
```python
from vertex_flow.workflow.vertex.vertex import SourceVertex, SinkVertex
from vertex_flow.workflow.workflow import Workflow, WorkflowContext

def source_func(inputs, context):
    return {"text": "Hello, Vertex Flow!"}

context = WorkflowContext()
workflow = Workflow(context)
source = SourceVertex(id="source", task=source_func)
workflow.add_vertex(source)
workflow.execute_workflow()
```

### Function Tools
```python
from vertex_flow.workflow.tools.functions import FunctionTool

def example_func(inputs, context):
    return {"result": inputs["value"] * 2}

tool = FunctionTool(
    name="example_tool",
    description="A simple example tool",
    func=example_func
)
```

### REST API
```bash
curl -X POST "http://localhost:8999/workflow" \
   -H "Content-Type: application/json" \
   -d '{
     "stream": true,
     "workflow_name": "research_workflow",
     "user_vars": {"topic": "AI trends"},
     "content": "Research latest AI developments"
   }'
```

## Project Structure

```
vertex/
├── vertex_flow/          # Core workflow engine
├── workflows/           # Workflow configuration files
├── web_ui/             # Web interface
├── docs/                # Project documentation
└── scripts/            # Helper scripts
```

## Documentation

For detailed information, please refer to the documentation:

### Project Documentation
- [Pre-commit Guide](docs/PRECOMMIT_README.md) - Development workflow and code quality checks
- [Configuration Sanitization](docs/SANITIZATION_README.md) - Security and configuration management

### Workflow Documentation
- [LLM Vertex](vertex_flow/docs/llm_vertex.md) - Language model integration
- [Function Vertex](vertex_flow/docs/function_vertex.md) - Custom function tools
- [VertexGroup](vertex_flow/docs/vertex_group.md) - Subgraph management
- [Web Search](vertex_flow/docs/web_search.md) - Web search capabilities
- [Embedding Vertex](vertex_flow/docs/embedding_vertex.md) - Text embedding processing
- [Vector Vertex](vertex_flow/docs/vector_vertex.md) - Vector operations
- [While Vertex](vertex_flow/docs/while_vertex.md) - Loop control structures

## Contributing

Contributions are welcome! Please check existing issues before submitting new ones.

## License

See LICENSE file for details.
