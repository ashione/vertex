# Vertex

Vertex is a tool that supports local and cloud-based large language model (LLM) inference and workflow orchestration, providing a simple and easy-to-use Web chat interface and powerful VertexFlow workflow engine. It supports locally deployed Qwen-7B models via Ollama, and can also call external models through APIs, supporting multi-model collaboration, knowledge base retrieval, embedding and reranking capabilities.

## Features

### Core Capabilities
- **Multi-Model Support**: Ollama local models and external APIs (OpenAI, DeepSeek, Claude)
- **Interactive Web UI**: Real-time chat with configuration management
- **Workflow Engine**: VertexFlow-based visual workflow orchestration

### Advanced Features
- **Function Tools**: Custom tool integration for workflows
- **Deep Research Workflow**: Multi-stage research with web search and structured output
- **VertexGroup**: Modular subgraph management with variable control and nesting

## Requirements

- Python 3.8 or higher
- Ollama (for local model inference, see https://ollama.com)

## Installation

1. Install Ollama

   - Visit [https://ollama.com/download](https://ollama.com/download)
   - Download and install Ollama for your system

2. Clone this repository

   ```bash
   git clone git@github.com:ashione/vertex.git
   cd vertex
   ```

3. Install dependencies

   ```bash
   pip install -r requirements.txt
   pip install -e .
   ```

## Quick Start

### Method 1: Command Line Start (Recommended)

```bash
vertex
```

### Method 2: Run Main Program Directly

```bash
python src/app.py
```

### Method 3: Development Mode

```bash
python -m src.app
```

### Method 4: VertexFlow Workflow Mode

```bash
python -m vertex_flow.src.app
```

After startup, visit [http://localhost:7860](http://localhost:7860) in your browser to access the Web chat interface (supports workflows and multi-models).

## Web UI User Guide

### Interface Overview

Vertex provides an intuitive and easy-to-use Web interface with the following main functional modules:

1. **Chat Interface** - Supports multi-turn conversations and streaming output
2. **Workflow Editor** - Visual workflow design and execution
3. **Configuration Management** - Model parameters and system settings

### Chat Features

#### Basic Chat
- Enter questions in the chat input box on the main page
- Supports multi-turn conversations with automatic context maintenance
- Supports real-time streaming output to see model generate responses word by word

#### Model Switching
- You can select different models in the chat interface:
  - `local-qwen`: Locally deployed Qwen-7B model via Ollama
  - `deepseek-chat`: DeepSeek API model
  - `openrouter/*`: Various models from OpenRouter platform

#### Custom System Prompt
- You can customize System Prompt in chat interface settings
- Used to guide model behavior and response style
- Supports real-time modification and application

### Workflow Editor Usage

#### Accessing Workflow Editor
- Click the "Workflow" button in the navigation bar
- Or directly visit [http://localhost:7860/workflow](http://localhost:7860/workflow)

#### Node Types
- **Start Node**: Entry point of the workflow
- **LLM Node**: Calls large language models for text generation
- **Retrieval Node**: Retrieves relevant information from knowledge base
- **Condition Node**: Performs branch judgment based on conditions
- **Function Node**: Executes custom function logic
- **End Node**: Exit point of the workflow

#### Creating Workflows
1. **Add Nodes**: Drag nodes from the left node panel to the canvas
2. **Connect Nodes**: Click connection mode, then click two nodes to establish connection
3. **Configure Nodes**: Select a node and configure parameters in the right properties panel
4. **Execute Workflow**: Click execute button to run the workflow
5. **View Output**: Check node execution results in the bottom output panel

#### Node Configuration Details

**LLM Node Configuration**:
- Model Selection: Supports local and cloud models
- System Prompt: Defines model behavior
- User Message: Supports variable placeholders
- Temperature: Controls output randomness (0-1)
- Max Tokens: Limits output length

**Retrieval Node Configuration**:
- Index Name: Specifies the knowledge base to retrieve from
- Query Content: Supports variable placeholders
- Retrieval Count: Number of relevant documents to return

**Condition Node Configuration**:
- Condition Expression: Uses Python expressions
- Supports multi-branch conditional judgment

#### Variable System
- **Environment Variables**: `{{#env.variable_name#}}`
- **User Variables**: `{{user.var.variable_name}}`
- **Node Output**: `{{node_id.output_field}}`

#### Workflow Operations
- **Save Workflow**: Auto-save to local
- **Load Workflow**: Load from configuration file
- **Export Workflow**: Export as YAML format
- **Auto Layout**: Automatically arrange node positions

### Output Panel Features

#### View Node Output
- Select an executed node to view results in the bottom output panel
- Supports Markdown format rendering
- Supports raw content viewing
- Supports one-click copy of output content

#### Panel Controls
- **Expand**: Expand output panel to full screen
- **Minimize**: Collapse output panel
- **Drag Resize**: Drag separator to adjust panel height

### Configuration Management

#### API Configuration
- Set external API keys and base URLs in the configuration page
- Supports multiple API services like DeepSeek, OpenRouter
- After configuration, you can use corresponding models in chat and workflows

#### Configuration File Security (Automatic Sanitization)
- **Automatic Sanitization**: The system automatically sanitizes sensitive information (API keys, secret keys) in configuration files before commits
- **Supported Formats**: Automatically detects and sanitizes `sk`, `api-key`, and similar sensitive fields
- **Manual Sanitization**: Run `python scripts/sanitize_config.py` to manually sanitize configuration files
- **Environment Variables**: Use environment variables to inject real API keys at runtime (e.g., `export llm_deepseek_sk="your-real-key"`)
- **Documentation**: See `docs/SANITIZATION_README.md` for detailed sanitization rules and usage

#### Model Parameters
- Temperature: Controls randomness and creativity of output
- Max Tokens: Limits maximum length of single output
- System Prompt: Global model behavior guidance

### Keyboard Shortcuts

- `Ctrl/Cmd + Enter`: Send chat message
- `Escape`: Cancel workflow node connection mode
- `Ctrl/Cmd + S`: Save workflow (in development)

## Development Guide

### Pre-commit Checks

The project integrates automated code quality checks and sensitive information sanitization to ensure security and quality of code commits.

#### Automatic Execution (Recommended)

Before each `git commit`, the system automatically executes pre-commit checks:

```bash
# Normal git commit workflow
git add .
git commit -m "your commit message"
```

The system automatically performs the following checks:
1. **Configuration File Sanitization**: Automatically detects and sanitizes sensitive information in `llm.yml` and other config files
2. **Code Quality Checks**: Runs flake8, black, isort and other tools to check code standards
3. **Sensitive Information Scanning**: Checks for any missed API keys, passwords, and other sensitive information

#### Manual Execution

To manually run pre-commit checks:

```bash
# Execute complete pre-commit checks
./scripts/precommit.sh

# Execute only configuration file sanitization
python scripts/sanitize_config.py
```

#### Pre-commit Check Details

**Configuration File Sanitization**:
- Automatically detects sensitive fields in `config/llm.yml`
- Supports multiple key formats like `sk`, `api-key`
- Sanitized format: `sk-***SANITIZED***`, `sk-or-***SANITIZED***`

**Code Quality Checks**:
- **flake8**: Python code style and syntax checking
- **black**: Code formatting checks
- **isort**: Import statement sorting checks

**Sensitive Information Scanning**:
- Checks staged files for API keys, passwords, and other sensitive information
- Supports multiple sensitive information pattern matching
- Prompts user for confirmation when sensitive information is found

#### Environment Variable Configuration

To use real API keys at runtime, it's recommended to configure environment variables:

```bash
# Add to ~/.bashrc or ~/.zshrc
export llm_deepseek_sk="your-real-deepseek-key"
export llm_openrouter_sk="your-real-openrouter-key"

# Or set temporarily at runtime
llm_deepseek_sk="your-key" python vertex_flow/src/app.py
```

#### Troubleshooting

**Pre-commit Check Failures**:
1. Check if Python environment has required dependencies installed correctly
2. Ensure code meets flake8, black, isort standards
3. Check for any unsanitized sensitive information

**Sanitization Function Issues**:
1. Ensure `scripts/sanitize_config.py` has execute permissions
2. Check if configuration file format is correct
3. See detailed documentation: `docs/SANITIZATION_README.md`

**More Information**:
- Pre-commit detailed documentation: `docs/PRECOMMIT_README.md`
- Sanitization feature documentation: `docs/SANITIZATION_README.md`

### Troubleshooting

#### Common Issues
1. **Workflow graph not displaying**:
   - Check browser console for JavaScript errors
   - Refresh page to reload
   - Ensure network connection is normal

2. **Node output not displaying**:
   - Ensure node has been successfully executed
   - Check if bottom output panel is minimized
   - Try reselecting the node

3. **Model call failure**:
   - Check if API key configuration is correct
   - Confirm network connection and API service status
   - Check console error messages

#### Performance Optimization Tips
- Execute large workflows step by step
- Clear browser cache regularly
- Use modern browsers for best experience

## Optional Parameters

- `--host`: Ollama service address (default: http://localhost:11434)
- `--port`: Web UI port (default: 7860)
- `--model`: Model name (local-qwen for local model, others for API models)
- `--api-key`: External API key (required when calling DeepSeek)
- `--api-base`: External API base URL
- `--config`: VertexFlow workflow configuration file (e.g., llm.yml)
- `system_prompt`: Supports custom System Prompt in Web UI

## Ollama Local Model Preparation

To automatically pull and configure local Qwen-7B model, run:

```bash
python scripts/setup_ollama.py
```

This script will automatically detect Ollama installation, service status, and pull required models.

## Example Code

### Building and Executing a Simple Workflow

```python
from vertex_flow.workflow.vertex.vertex import SourceVertex, SinkVertex
from vertex_flow.workflow.workflow import Workflow, WorkflowContext

def source_func(inputs, context):
    return {"text": "Hello, Vertex Flow!"}

def sink_func(inputs, context):
    print("Workflow output:", inputs["source"])

context = WorkflowContext()
workflow = Workflow(context)
source = SourceVertex(id="source", task=source_func)
sink = SinkVertex(id="sink", task=sink_func)
workflow.add_vertex(source)
workflow.add_vertex(sink)
source | sink
workflow.execute_workflow()
```
          
## Function Tools Documentation

Function Tools is part of VertexFlow, designed to enhance workflow orchestration and real-time chat interaction capabilities. It allows users to define and register custom function tools for dynamic invocation in workflows.

### How to Define Function Tools

To define a Function Tool, you need to create a `FunctionTool` instance with the following parameters:
- `name`: Tool name
- `description`: Tool description
- `func`: The actual function to execute
- `schema`: JSON Schema for parameters (optional)

### Example Code

Here's a simple Function Tool example:

```python
from vertex_flow.workflow.tools.functions import FunctionTool

def example_func(inputs, context):
    return {"result": inputs["value"] * 2}

example_tool = FunctionTool(
    name="example_tool",
    description="A simple example tool",
    func=example_func,
    schema={"type": "object", "properties": {"value": {"type": "integer"}}}
)
```

### How to Register Function Tools

After registering Function Tools, you can dynamically invoke them in `LLMVertex`. Ensure the tool description complies with LLM protocol requirements.

### Usage

In workflows, you can invoke registered Function Tools through `LLMVertex` and process their return results.

Hope this information helps you better understand and use Function Tools.

## Example Use Cases

Here's an example of using `curl` command to interact with the API:

### Streaming Workflow Execution

You can use the following `curl` command to execute a streaming workflow request:

```bash
curl -X POST "http://localhost:8999/workflow" --no-buffer \
   -H "Content-Type: application/json" -H "Accept: text/event-stream" \
   -d '{
     "stream": true,
     "workflow_name": "if_else_test-2",
     "env_vars": {},
     "user_vars": {"text": "333"},
     "content": "What stories happened in history on May 18, 2025? Please list 10 main ones first."
   }'
```

#### Parameter Description

- `stream`: Specifies whether to use streaming mode, `true` enables streaming mode.
- `workflow_name`: Name of the workflow.
- `env_vars`: Dictionary of environment variables.
- `user_vars`: Dictionary of user variables.
- `content`: Text content to be processed.

#### Return Results

This request will return a streaming response containing workflow execution results. Each result block will be returned in JSON format, including the following fields:
- `output`: Processed output content.
- `status`: Execution status, `true` indicates success.
- `message`: Error message (if any).

## API Documentation

- `Workflow.add_vertex(vertex)`: Add vertex to workflow.
- `vertex1 | vertex2`: Connect two vertices, automatically add edge.
- `Workflow.execute_workflow(source_inputs)`: Execute workflow, can pass initial inputs.
- `Workflow.result()`: Get output results from SINK vertex.
- `WorkflowContext`: Used to manage environment parameters, user parameters, and vertex outputs.

## Dify Workflow Compatibility

- Supports Dify-style variable placeholders (e.g., `{{#env.xxx#}}`, `{{user.var.xxx}}`).
- `WorkflowContext` supports environment and user parameters for easy integration with Dify workflow parameter system.
- Vertex types (such as LLM, Embedding, Rerank, IfElse) can directly map to Dify workflow nodes.
- `IfElseVertex` supports multi-condition branching, compatible with Dify's conditional jump logic.
- Supports serialization and deserialization of YAML workflow structures for easy interoperability with Dify workflow configuration files.

## FAQ

- Startup error "Cannot connect to Ollama service": Please ensure Ollama is installed and started. You can manually open the Ollama app or run `python scripts/setup_ollama.py`.
- When calling external models, please configure API Key and Base URL in Web UI.
- If you encounter API connection issues, please check network connection and verify API key is correct.
- In VertexFlow workflow mode, it's recommended to refer to `config/llm.yml` for configuring multi-model and knowledge base parameters.
- To customize system prompt, you can fill it directly in the Web UI.

## Directory Structure

```
localqwen/
├── vertex_flow/            # Core workflow engine with multi-model collaboration and advanced workflows
├── web_ui/                 # Web user interface providing visual operation interface
├── scripts/                # Development and deployment scripts with pre-commit checks and config sanitization
├── docs/                   # Project documentation including development guides and usage instructions
├── config/                 # Configuration files directory for LLM and other configurations
├── .github/                # GitHub Actions workflow configurations
└── Other config files      # Python project configuration, dependency management, etc.
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

### Main Module Description

- **vertex_flow/**: Core workflow engine including multi-model clients, workflow management, vector processing, etc.
- **web_ui/**: Web user interface providing chat, configuration management, workflow visualization, etc.
- **scripts/**: Development tool scripts including environment setup, pre-commit checks, config sanitization, etc.
- **docs/**: Project documentation including detailed usage guides and development instructions
- **config/**: Configuration file storage directory supporting multiple LLM service configurations

## Development Roadmap

- [ ] Support for more local models (such as LLaMA, Mistral, etc.)
- [ ] Add knowledge base retrieval functionality
- [ ] Support document upload and analysis
- [ ] Add chart generation functionality
- [ ] Provide API service interface
- [ ] Workflow visualization and multi-model collaboration
- [ ] Support custom tool invocation and plugin extensions

## Contributing

Welcome to submit Pull Requests or Issues to help improve the project. Please check existing Issues before contributing to ensure no duplicate work.
