"""Path finding algorithms: BFS shortest, DFS all paths."""

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING

from decoder.core.graph.models import Path

if TYPE_CHECKING:
    from decoder.core.graph.base import CallGraph
    from decoder.core.models import Edge


def shortest_path(graph: CallGraph, from_id: int, to_id: int) -> Path | None:
    """Find shortest path using BFS. O(V + E)."""
    if from_id not in graph.symbols or to_id not in graph.symbols:
        return None
    if from_id == to_id:
        return Path(nodes=[graph.symbols[from_id]], edges=[])

    queue: deque[int] = deque([from_id])
    parent: dict[int, tuple[int, Edge]] = {}
    visited: set[int] = {from_id}

    while queue:
        current = queue.popleft()
        for callee_id, edge in graph._out.get(current, []):
            if callee_id not in visited:
                visited.add(callee_id)
                parent[callee_id] = (current, edge)
                if callee_id == to_id:
                    return _reconstruct(graph, from_id, to_id, parent)
                queue.append(callee_id)

    return None


def all_paths(
    graph: CallGraph,
    from_id: int,
    to_id: int,
    max_paths: int = 100,
    max_depth: int = 20,
) -> list[Path]:
    """Find all paths using DFS with backtracking.

    Limited by max_paths and max_depth to avoid explosion.
    """
    if from_id not in graph.symbols or to_id not in graph.symbols:
        return []

    paths: list[Path] = []
    current_nodes: list[int] = [from_id]
    current_edges: list[Edge] = []
    visited: set[int] = {from_id}

    def dfs(node_id: int, depth: int) -> None:
        if len(paths) >= max_paths or depth > max_depth:
            return

        if node_id == to_id:
            paths.append(
                Path(
                    nodes=[graph.symbols[n] for n in current_nodes],
                    edges=list(current_edges),
                )
            )
            return

        for callee_id, edge in graph._out.get(node_id, []):
            if callee_id not in visited:
                visited.add(callee_id)
                current_nodes.append(callee_id)
                current_edges.append(edge)

                dfs(callee_id, depth + 1)

                current_nodes.pop()
                current_edges.pop()
                visited.remove(callee_id)

    dfs(from_id, 0)
    return paths


def _reconstruct(
    graph: CallGraph, from_id: int, to_id: int, parent: dict[int, tuple[int, Edge]]
) -> Path:
    """Reconstruct path from BFS parent map."""
    nodes = []
    edges = []
    current = to_id

    while current != from_id:
        nodes.append(graph.symbols[current])
        prev, edge = parent[current]
        edges.append(edge)
        current = prev

    nodes.append(graph.symbols[from_id])
    nodes.reverse()
    edges.reverse()
    return Path(nodes=nodes, edges=edges)
