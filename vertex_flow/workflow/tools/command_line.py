#!/usr/bin/env python3
"""
Command Line Function Tool - 支持本地命令行执行
"""

import json
import logging
import os
import subprocess
import sys
from typing import Any, Dict, Optional

from vertex_flow.workflow.tools.functions import FunctionTool

logger = logging.getLogger(__name__)


def execute_command(inputs: Dict[str, Any], context: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Execute a command line command

    Args:
        inputs: Dictionary containing:
            - command: str, the command to execute
            - timeout: int, optional, timeout in seconds (default: 30)
            - working_dir: str, optional, working directory (default: current dir)
            - capture_output: bool, optional, whether to capture output (default: True)
            - shell: bool, optional, whether to use shell (default: True for safety)
        context: Optional execution context

    Returns:
        Dictionary containing:
            - success: bool, whether command executed successfully
            - exit_code: int, the exit code
            - stdout: str, standard output
            - stderr: str, standard error
            - command: str, the executed command
            - working_dir: str, the working directory used
    """

    # Extract parameters
    command = inputs.get("command", "").strip()
    timeout = inputs.get("timeout", 30)
    working_dir = inputs.get("working_dir", os.getcwd())
    capture_output = inputs.get("capture_output", True)
    use_shell = inputs.get("shell", True)

    if not command:
        return {
            "success": False,
            "exit_code": -1,
            "stdout": "",
            "stderr": "Error: No command provided",
            "command": command,
            "working_dir": working_dir,
        }

    logger.info(f"Executing command: {command} in directory: {working_dir}")

    # Security check - basic command validation
    dangerous_commands = ["rm -rf /", "sudo rm", "del /s /q", "format", "fdisk"]
    if any(dangerous in command.lower() for dangerous in dangerous_commands):
        logger.warning(f"Potentially dangerous command blocked: {command}")
        return {
            "success": False,
            "exit_code": -1,
            "stdout": "",
            "stderr": "Error: Potentially dangerous command blocked for security",
            "command": command,
            "working_dir": working_dir,
        }

    try:
        # Ensure working directory exists
        if not os.path.exists(working_dir):
            os.makedirs(working_dir, exist_ok=True)

        # Execute command
        if capture_output:
            result = subprocess.run(
                command,
                shell=use_shell,
                cwd=working_dir,
                timeout=timeout,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

            stdout = result.stdout or ""
            stderr = result.stderr or ""
            exit_code = result.returncode

        else:
            # For commands that don't need output capture (like interactive commands)
            result = subprocess.run(command, shell=use_shell, cwd=working_dir, timeout=timeout)
            stdout = ""
            stderr = ""
            exit_code = result.returncode

        success = exit_code == 0

        logger.info(f"Command completed with exit code: {exit_code}")

        return {
            "success": success,
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
            "command": command,
            "working_dir": working_dir,
        }

    except subprocess.TimeoutExpired:
        logger.error(f"Command timed out after {timeout} seconds")
        return {
            "success": False,
            "exit_code": -2,
            "stdout": "",
            "stderr": f"Command timed out after {timeout} seconds",
            "command": command,
            "working_dir": working_dir,
        }

    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed with exit code {e.returncode}: {e}")
        return {
            "success": False,
            "exit_code": e.returncode,
            "stdout": e.stdout or "",
            "stderr": e.stderr or "",
            "command": command,
            "working_dir": working_dir,
        }

    except Exception as e:
        logger.error(f"Unexpected error executing command: {e}")
        return {
            "success": False,
            "exit_code": -3,
            "stdout": "",
            "stderr": f"Unexpected error: {str(e)}",
            "command": command,
            "working_dir": working_dir,
        }


def create_command_line_tool() -> FunctionTool:
    """
    Create a command line function tool

    Returns:
        FunctionTool: 配置好的FunctionTool实例，可直接用于function calling
    """

    schema = {
        "type": "function",
        "function": {
            "name": "execute_command",
            "description": "Execute a command line command on the local system. Can run shell commands, scripts, and system utilities. Use with caution and avoid destructive operations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The command to execute (e.g., 'ls -la', 'python --version', 'git status')",
                    },
                    "timeout": {"type": "integer", "description": "Timeout in seconds (default: 30)", "default": 30},
                    "working_dir": {
                        "type": "string",
                        "description": "Working directory for command execution (default: current directory)",
                    },
                    "capture_output": {
                        "type": "boolean",
                        "description": "Whether to capture command output (default: true)",
                        "default": True,
                    },
                    "shell": {
                        "type": "boolean",
                        "description": "Whether to use shell for command execution (default: true)",
                        "default": True,
                    },
                },
                "required": ["command"],
            },
        },
    }

    return FunctionTool(
        name="execute_command",
        description="Execute command line commands on the local system",
        func=execute_command,
        schema=schema,
    )


# Example usage and test functions
def test_command_line_tool():
    """Test the command line tool"""
    tool = create_command_line_tool()

    # Test basic command
    print("=== Testing basic command (pwd) ===")
    result = tool.execute({"command": "pwd"})
    print(f"Result: {json.dumps(result, indent=2)}")

    # Test command with parameters
    print("\n=== Testing ls command ===")
    result = tool.execute({"command": "ls -la", "timeout": 10})
    print(f"Result: {json.dumps(result, indent=2)}")

    # Test Python command
    print("\n=== Testing Python version ===")
    result = tool.execute({"command": "python --version"})
    print(f"Result: {json.dumps(result, indent=2)}")


if __name__ == "__main__":
    test_command_line_tool()
