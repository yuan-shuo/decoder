"""Data models for graph operations."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from decoder.core.models import Edge, Symbol


@dataclass
class TreeNode:
    """A node in the call tree with full context."""

    symbol: Symbol
    edge: Edge | None
    depth: int
    children: list[TreeNode] = field(default_factory=list)

    @property
    def is_conditional(self) -> bool:
        return self.edge.is_conditional if self.edge else False

    @property
    def condition(self) -> str | None:
        return self.edge.condition if self.edge else None

    @property
    def is_loop(self) -> bool:
        return self.edge.is_loop if self.edge else False

    @property
    def is_try_block(self) -> bool:
        return self.edge.is_try_block if self.edge else False

    def __iter__(self) -> Iterator[TreeNode]:
        """Pre-order traversal."""
        yield self
        for child in self.children:
            yield from child

    def __len__(self) -> int:
        """Total nodes in subtree."""
        return 1 + sum(len(c) for c in self.children)


@dataclass
class Path:
    """A path through the call graph."""

    nodes: list[Symbol]
    edges: list[Edge]

    def __len__(self) -> int:
        return len(self.nodes)

    def __iter__(self) -> Iterator[Symbol]:
        return iter(self.nodes)

    def __repr__(self) -> str:
        names = " -> ".join(n.name for n in self.nodes)
        return f"Path({names})"
