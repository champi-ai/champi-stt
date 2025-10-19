"""
Command action executors
"""

import asyncio
# import logging - replaced with loguru
import subprocess
from enum import Enum
from dataclasses import dataclass
from typing import Any, Optional
import json

from loguru import logger


class ActionType(Enum):
    """Types of command actions"""
    SHELL = "shell"  # Execute shell command
    API = "api"  # HTTP API call
    PYTHON = "python"  # Python function call


@dataclass
class CommandAction:
    """Represents a command action configuration"""
    type: ActionType
    value: Any  # Shell command, API URL, or Python function path
    params: Optional[dict[str, Any]] = None  # Additional parameters


class CommandExecutor:
    """
    Executes different types of command actions.

    Supports:
    - Shell commands
    - HTTP API calls
    - Python function invocations
    """

    async def execute_shell(
        self,
        command: str,
        timeout: int = 30,
        **kwargs
    ) -> dict[str, Any]:
        """
        Execute shell command.

        Args:
            command: Shell command to execute
            timeout: Timeout in seconds
            **kwargs: Arguments to format into command

        Returns:
            Result dict with stdout, stderr, return_code

        Example:
            executor.execute_shell("echo {message}", message="Hello")
        """
        # Format command with kwargs
        if kwargs:
            try:
                command = command.format(**kwargs)
            except KeyError as e:
                logger.error(f"Missing parameter for command: {e}")
                raise

        logger.info(f"Executing shell command: {command}")

        try:
            # Run command with timeout
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )

            result = {
                "success": process.returncode == 0,
                "return_code": process.returncode,
                "stdout": stdout.decode() if stdout else "",
                "stderr": stderr.decode() if stderr else "",
            }

            if result["success"]:
                logger.info(f"✓ Command executed successfully")
            else:
                logger.warning(f"Command failed with code {process.returncode}")

            return result

        except asyncio.TimeoutError:
            logger.error(f"Command timed out after {timeout}s")
            return {
                "success": False,
                "error": "timeout",
                "message": f"Command timed out after {timeout}s"
            }
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def execute_api(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[dict] = None,
        data: Optional[dict] = None,
        timeout: int = 30,
        **kwargs
    ) -> dict[str, Any]:
        """
        Execute HTTP API call.

        Args:
            url: API endpoint URL
            method: HTTP method (GET, POST, PUT, DELETE)
            headers: HTTP headers
            data: Request body data
            timeout: Timeout in seconds
            **kwargs: Arguments to format into URL/data

        Returns:
            Result dict with status, response data
        """
        import aiohttp

        # Format URL and data with kwargs
        if kwargs:
            url = url.format(**kwargs)
            if data:
                data = {k: v.format(**kwargs) if isinstance(v, str) else v
                       for k, v in data.items()}

        logger.info(f"Executing API call: {method} {url}")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method,
                    url,
                    headers=headers,
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as response:
                    result = {
                        "success": response.status < 400,
                        "status": response.status,
                        "headers": dict(response.headers),
                    }

                    # Try to parse JSON response
                    try:
                        result["data"] = await response.json()
                    except:
                        result["data"] = await response.text()

                    if result["success"]:
                        logger.info(f"✓ API call successful: {response.status}")
                    else:
                        logger.warning(f"API call failed: {response.status}")

                    return result

        except asyncio.TimeoutError:
            logger.error(f"API call timed out after {timeout}s")
            return {
                "success": False,
                "error": "timeout"
            }
        except Exception as e:
            logger.error(f"API call failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def execute_python(
        self,
        function_path: str,
        **kwargs
    ) -> Any:
        """
        Execute Python function by import path.

        Args:
            function_path: Dotted path to function (e.g., "module.function")
            **kwargs: Arguments to pass to function

        Returns:
            Function result
        """
        logger.info(f"Executing Python function: {function_path}")

        try:
            # Import function dynamically
            module_path, func_name = function_path.rsplit(".", 1)
            module = __import__(module_path, fromlist=[func_name])
            func = getattr(module, func_name)

            # Execute function (async or sync)
            if asyncio.iscoroutinefunction(func):
                result = await func(**kwargs)
            else:
                result = func(**kwargs)

            logger.info(f"✓ Function executed successfully")
            return result

        except Exception as e:
            logger.error(f"Python function execution failed: {e}")
            raise

    async def execute_action(
        self,
        action: CommandAction,
        **kwargs
    ) -> Any:
        """
        Execute command action based on type.

        Args:
            action: CommandAction configuration
            **kwargs: Runtime arguments

        Returns:
            Action result
        """
        # Merge action params with runtime kwargs
        params = {**(action.params or {}), **kwargs}

        if action.type == ActionType.SHELL:
            return await self.execute_shell(action.value, **params)

        elif action.type == ActionType.API:
            return await self.execute_api(action.value, **params)

        elif action.type == ActionType.PYTHON:
            return await self.execute_python(action.value, **params)

        else:
            raise ValueError(f"Unknown action type: {action.type}")
