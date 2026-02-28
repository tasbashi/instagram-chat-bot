"""Tool base class and registry."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):
    """Base class for all agent tools."""

    name: str
    description: str
    parameters: dict[str, Any]

    @abstractmethod
    async def execute(self, args: dict[str, Any], context: dict[str, Any]) -> str:
        """Execute the tool and return a string result for the LLM."""
        ...

    def to_openai_schema(self) -> dict[str, Any]:
        """Convert to OpenAI function-calling tool schema."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    """Registry of available tools for an agent."""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def get_schemas(self, permissions: dict[str, bool]) -> list[dict[str, Any]]:
        """Get OpenAI tool schemas filtered by agent permissions."""
        schemas = []
        for tool in self._tools.values():
            # Always include search_knowledge and collect_compliment
            if tool.name in ("search_knowledge", "collect_compliment"):
                schemas.append(tool.to_openai_schema())
            elif tool.name == "send_email" and permissions.get("send_email"):
                schemas.append(tool.to_openai_schema())
            elif tool.name == "manage_appointment" and permissions.get("manage_appointments"):
                schemas.append(tool.to_openai_schema())
        return schemas

    @property
    def all_tools(self) -> dict[str, BaseTool]:
        return self._tools
