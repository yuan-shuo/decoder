"""Tree extraction using DFS traversal."""

from __future__ import annotations

from typing import TYPE_CHECKING

from decoder.core.graph.models import TreeNode

if TYPE_CHECKING:
    from decoder.core.graph.base import CallGraph
    from decoder.core.models import Edge


def get_callee_tree(graph: CallGraph, root_id: int, max_depth: int = 10) -> TreeNode | None:
    """Build call tree of all callees from root.

    DFS with cycle detection. O(V + E) in subgraph.
    """
    if root_id not in graph.symbols:
        return None

    visited: set[int] = set()

    def dfs(symbol_id: int, edge: Edge | None, depth: int) -> TreeNode | None:
        if depth > max_depth or symbol_id in visited:
            return None
        if symbol_id not in graph.symbols:
            return None

        visited.add(symbol_id)
        node = TreeNode(
            symbol=graph.symbols[symbol_id],
            edge=edge,
            depth=depth,
        )

        callees = sorted(
            graph._out.get(symbol_id, []),
            key=lambda x: x[1].call_line,
        )
        for callee_id, callee_edge in callees:
            child = dfs(callee_id, callee_edge, depth + 1)
            if child:
                node.children.append(child)

        visited.remove(symbol_id)
        return node

    return dfs(root_id, None, 0)


def get_caller_tree(graph: CallGraph, root_id: int, max_depth: int = 10) -> TreeNode | None:
    """Build tree of all callers leading to root.

    DFS going backwards. O(V + E) in subgraph.
    """
    if root_id not in graph.symbols:
        return None

    visited: set[int] = set()

    def dfs(symbol_id: int, edge: Edge | None, depth: int) -> TreeNode | None:
        if depth > max_depth or symbol_id in visited:
            return None
        if symbol_id not in graph.symbols:
            return None

        visited.add(symbol_id)
        node = TreeNode(
            symbol=graph.symbols[symbol_id],
            edge=edge,
            depth=depth,
        )

        callers = sorted(
            graph._in.get(symbol_id, []),
            key=lambda x: x[1].call_line,
        )
        for caller_id, caller_edge in callers:
            child = dfs(caller_id, caller_edge, depth + 1)
            if child:
                node.children.append(child)

        visited.remove(symbol_id)
        return node

    return dfs(root_id, None, 0)


def flatten_tree(root: TreeNode, include_root: bool = True) -> list[TreeNode]:
    """Flatten tree to list in pre-order. O(n)."""
    result: list[TreeNode] = []
    if include_root:
        result.append(root)
    for child in root.children:
        result.extend(flatten_tree(child, include_root=True))
    return result
