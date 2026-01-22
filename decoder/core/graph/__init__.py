"""
Call graph data structures and algorithms.

This module provides in-memory graph operations for analyzing call relationships:

Data Structures:
    - CallGraph: Adjacency list representation with O(1) lookups
    - TreeNode: Tree representation for caller/callee hierarchies
    - Path: A sequence of symbols representing a call chain

Algorithms:
    - traversal: DFS tree extraction (get_callee_tree, get_caller_tree)
    - pathfinding: BFS shortest path, DFS all paths
    - analysis: Cycle detection, entry points, topological sort

Loading:
    - load_from_repository(): Load full graph from SQLite
    - load_subgraph(): Load only reachable nodes (memory efficient)
"""

from decoder.core.graph.base import CallGraph
from decoder.core.graph.loader import load_from_repository, load_subgraph
from decoder.core.graph.models import Path, TreeNode

__all__ = [
    "CallGraph",
    "Path",
    "TreeNode",
    "load_from_repository",
    "load_subgraph",
]
