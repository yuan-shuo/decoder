"""Unit tests for graph algorithms."""

from pathlib import Path

import pytest

from decoder.core.graph import CallGraph
from decoder.core.graph.analysis import (
    find_cycles,
    get_entry_points,
    get_hot_paths,
    get_leaf_functions,
    has_cycle,
    topological_sort,
)
from decoder.core.graph.pathfinding import all_paths, shortest_path
from decoder.core.graph.traversal import get_callee_tree, get_caller_tree
from decoder.core.models import Edge, EdgeType, Symbol, SymbolType


def make_symbol(id: int, name: str) -> Symbol:
    """Create a test symbol."""
    return Symbol(
        id=id,
        name=name,
        qualified_name=f"test.{name}",
        file=Path("test.py"),
        line=id * 10,
        end_line=id * 10 + 5,
        type=SymbolType.FUNCTION,
        parent_id=None,
    )


def make_edge(id: int, caller_id: int, callee_id: int) -> Edge:
    """Create a test edge."""
    return Edge(
        id=id,
        caller_id=caller_id,
        callee_id=callee_id,
        call_line=caller_id * 10 + 1,
        call_type=EdgeType.CALL,
    )


@pytest.fixture
def linear_graph() -> CallGraph:
    """Create a linear graph: A -> B -> C -> D."""
    graph = CallGraph()
    for i, name in enumerate(["A", "B", "C", "D"], start=1):
        graph.add_symbol(make_symbol(i, name))
    graph.add_edge(make_edge(1, 1, 2))  # A -> B
    graph.add_edge(make_edge(2, 2, 3))  # B -> C
    graph.add_edge(make_edge(3, 3, 4))  # C -> D
    return graph


@pytest.fixture
def branching_graph() -> CallGraph:
    r"""Create a branching graph: A -> B -> D, A -> C -> D (diamond shape)."""
    graph = CallGraph()
    for i, name in enumerate(["A", "B", "C", "D"], start=1):
        graph.add_symbol(make_symbol(i, name))
    graph.add_edge(make_edge(1, 1, 2))  # A -> B
    graph.add_edge(make_edge(2, 1, 3))  # A -> C
    graph.add_edge(make_edge(3, 2, 4))  # B -> D
    graph.add_edge(make_edge(4, 3, 4))  # C -> D
    return graph


@pytest.fixture
def cyclic_graph() -> CallGraph:
    """Create a graph with a cycle: A -> B -> C -> A."""
    graph = CallGraph()
    for i, name in enumerate(["A", "B", "C"], start=1):
        graph.add_symbol(make_symbol(i, name))
    graph.add_edge(make_edge(1, 1, 2))  # A -> B
    graph.add_edge(make_edge(2, 2, 3))  # B -> C
    graph.add_edge(make_edge(3, 3, 1))  # C -> A (cycle)
    return graph


@pytest.fixture
def disconnected_graph() -> CallGraph:
    """Create a disconnected graph: A -> B, C -> D (two separate components)."""
    graph = CallGraph()
    for i, name in enumerate(["A", "B", "C", "D"], start=1):
        graph.add_symbol(make_symbol(i, name))
    graph.add_edge(make_edge(1, 1, 2))  # A -> B
    graph.add_edge(make_edge(2, 3, 4))  # C -> D
    return graph


class TestCallGraph:
    """Tests for the CallGraph class."""

    def test_add_symbol(self) -> None:
        graph = CallGraph()
        symbol = make_symbol(1, "test")
        graph.add_symbol(symbol)
        assert 1 in graph.symbols
        assert graph.symbols[1].name == "test"

    def test_add_edge(self) -> None:
        graph = CallGraph()
        graph.add_symbol(make_symbol(1, "A"))
        graph.add_symbol(make_symbol(2, "B"))
        graph.add_edge(make_edge(1, 1, 2))

        assert len(graph.get_callees(1)) == 1
        assert len(graph.get_callers(2)) == 1

    def test_get_callees_empty(self) -> None:
        graph = CallGraph()
        graph.add_symbol(make_symbol(1, "A"))
        assert graph.get_callees(1) == []

    def test_get_callers_empty(self) -> None:
        graph = CallGraph()
        graph.add_symbol(make_symbol(1, "A"))
        assert graph.get_callers(1) == []


class TestCycleDetection:
    """Tests for cycle detection algorithms."""

    def test_has_cycle_false(self, linear_graph: CallGraph) -> None:
        assert has_cycle(linear_graph) is False

    def test_has_cycle_true(self, cyclic_graph: CallGraph) -> None:
        assert has_cycle(cyclic_graph) is True

    def test_has_cycle_branching(self, branching_graph: CallGraph) -> None:
        assert has_cycle(branching_graph) is False

    def test_find_cycles_none(self, linear_graph: CallGraph) -> None:
        cycles = find_cycles(linear_graph)
        assert len(cycles) == 0

    def test_find_cycles_one(self, cyclic_graph: CallGraph) -> None:
        cycles = find_cycles(cyclic_graph)
        assert len(cycles) == 1
        cycle_names = [s.name for s in cycles[0]]
        assert set(cycle_names) == {"A", "B", "C"}

    def test_find_cycles_max_limit(self) -> None:
        """Test that max_cycles limit is respected."""
        graph = CallGraph()
        # Create multiple small cycles
        for i in range(1, 7):
            graph.add_symbol(make_symbol(i, f"N{i}"))
        # Two separate cycles: 1->2->1, 3->4->3, 5->6->5
        graph.add_edge(make_edge(1, 1, 2))
        graph.add_edge(make_edge(2, 2, 1))
        graph.add_edge(make_edge(3, 3, 4))
        graph.add_edge(make_edge(4, 4, 3))
        graph.add_edge(make_edge(5, 5, 6))
        graph.add_edge(make_edge(6, 6, 5))

        cycles = find_cycles(graph, max_cycles=2)
        assert len(cycles) <= 2


class TestEntryAndLeafPoints:
    """Tests for entry point and leaf function detection."""

    def test_get_entry_points_linear(self, linear_graph: CallGraph) -> None:
        entries = get_entry_points(linear_graph)
        assert len(entries) == 1
        assert entries[0].name == "A"

    def test_get_entry_points_disconnected(self, disconnected_graph: CallGraph) -> None:
        entries = get_entry_points(disconnected_graph)
        names = {e.name for e in entries}
        assert names == {"A", "C"}

    def test_get_leaf_functions_linear(self, linear_graph: CallGraph) -> None:
        leaves = get_leaf_functions(linear_graph)
        assert len(leaves) == 1
        assert leaves[0].name == "D"

    def test_get_leaf_functions_branching(self, branching_graph: CallGraph) -> None:
        leaves = get_leaf_functions(branching_graph)
        assert len(leaves) == 1
        assert leaves[0].name == "D"


class TestHotPaths:
    """Tests for hot path detection."""

    def test_get_hot_paths_branching(self, branching_graph: CallGraph) -> None:
        """D has highest connectivity (2 in, 0 out), A has (0 in, 2 out)."""
        hot = get_hot_paths(branching_graph, top_k=2)
        # A and D both have connectivity 2, B and C have 2 each as well
        assert len(hot) == 2

    def test_get_hot_paths_respects_limit(self, linear_graph: CallGraph) -> None:
        hot = get_hot_paths(linear_graph, top_k=2)
        assert len(hot) == 2


class TestTopologicalSort:
    """Tests for topological sort."""

    def test_topological_sort_linear(self, linear_graph: CallGraph) -> None:
        result = topological_sort(linear_graph)
        assert result is not None
        names = [s.name for s in result]
        assert names == ["A", "B", "C", "D"]

    def test_topological_sort_branching(self, branching_graph: CallGraph) -> None:
        result = topological_sort(branching_graph)
        assert result is not None
        names = [s.name for s in result]
        # A must come first, D must come last
        assert names[0] == "A"
        assert names[-1] == "D"

    def test_topological_sort_cyclic_returns_none(self, cyclic_graph: CallGraph) -> None:
        result = topological_sort(cyclic_graph)
        assert result is None


class TestTraversal:
    """Tests for tree traversal."""

    def test_get_callee_tree_linear(self, linear_graph: CallGraph) -> None:
        tree = get_callee_tree(linear_graph, root_id=1, max_depth=10)
        assert tree is not None
        assert tree.symbol.name == "A"
        assert len(tree.children) == 1
        assert tree.children[0].symbol.name == "B"

    def test_get_callee_tree_respects_depth(self, linear_graph: CallGraph) -> None:
        tree = get_callee_tree(linear_graph, root_id=1, max_depth=1)
        assert tree is not None
        assert len(tree.children) == 1
        # At depth 1, we see A and B, but B's children are cut off
        assert tree.children[0].symbol.name == "B"
        assert len(tree.children[0].children) == 0

    def test_get_callee_tree_nonexistent_root(self, linear_graph: CallGraph) -> None:
        tree = get_callee_tree(linear_graph, root_id=999, max_depth=10)
        assert tree is None

    def test_get_caller_tree_linear(self, linear_graph: CallGraph) -> None:
        tree = get_caller_tree(linear_graph, root_id=4, max_depth=10)
        assert tree is not None
        assert tree.symbol.name == "D"
        assert len(tree.children) == 1
        assert tree.children[0].symbol.name == "C"

    def test_get_caller_tree_branching(self, branching_graph: CallGraph) -> None:
        tree = get_caller_tree(branching_graph, root_id=4, max_depth=10)
        assert tree is not None
        assert tree.symbol.name == "D"
        # D has two callers: B and C
        assert len(tree.children) == 2
        caller_names = {c.symbol.name for c in tree.children}
        assert caller_names == {"B", "C"}


class TestPathfinding:
    """Tests for path finding algorithms."""

    def test_shortest_path_linear(self, linear_graph: CallGraph) -> None:
        path = shortest_path(linear_graph, from_id=1, to_id=4)
        assert path is not None
        assert len(path.nodes) == 4
        names = [n.name for n in path.nodes]
        assert names == ["A", "B", "C", "D"]

    def test_shortest_path_same_node(self, linear_graph: CallGraph) -> None:
        path = shortest_path(linear_graph, from_id=1, to_id=1)
        assert path is not None
        assert len(path.nodes) == 1
        assert path.nodes[0].name == "A"

    def test_shortest_path_no_path(self, disconnected_graph: CallGraph) -> None:
        path = shortest_path(disconnected_graph, from_id=1, to_id=4)
        assert path is None

    def test_shortest_path_nonexistent_node(self, linear_graph: CallGraph) -> None:
        path = shortest_path(linear_graph, from_id=1, to_id=999)
        assert path is None

    def test_all_paths_linear(self, linear_graph: CallGraph) -> None:
        paths = all_paths(linear_graph, from_id=1, to_id=4)
        assert len(paths) == 1
        names = [n.name for n in paths[0].nodes]
        assert names == ["A", "B", "C", "D"]

    def test_all_paths_branching(self, branching_graph: CallGraph) -> None:
        paths = all_paths(branching_graph, from_id=1, to_id=4)
        assert len(paths) == 2
        # Two paths: A->B->D and A->C->D
        path_names = [tuple(n.name for n in p.nodes) for p in paths]
        assert ("A", "B", "D") in path_names
        assert ("A", "C", "D") in path_names

    def test_all_paths_no_path(self, disconnected_graph: CallGraph) -> None:
        paths = all_paths(disconnected_graph, from_id=1, to_id=4)
        assert len(paths) == 0

    def test_all_paths_respects_max(self, branching_graph: CallGraph) -> None:
        paths = all_paths(branching_graph, from_id=1, to_id=4, max_paths=1)
        assert len(paths) == 1


class TestTreeNode:
    """Tests for TreeNode iteration and length."""

    def test_tree_node_len(self, linear_graph: CallGraph) -> None:
        tree = get_callee_tree(linear_graph, root_id=1, max_depth=10)
        assert tree is not None
        assert len(tree) == 4  # A, B, C, D

    def test_tree_node_iter(self, linear_graph: CallGraph) -> None:
        tree = get_callee_tree(linear_graph, root_id=1, max_depth=10)
        assert tree is not None
        names = [node.symbol.name for node in tree]
        assert names == ["A", "B", "C", "D"]
