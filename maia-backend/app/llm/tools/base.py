from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):
    name: str
    description: str

    @abstractmethod
    def run(self, **kwargs: Any) -> Any:
        ...


# Registry vazio em v1 — adicionar tools aqui nas sprints futuras
TOOL_REGISTRY: list[type[BaseTool]] = []
