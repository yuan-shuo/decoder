"""Core CallGraph class with adjacency list representation."""

from __future__ import annotations

from decoder.core.models import Edge, Symbol


class CallGraph:
    """Directed graph for call relationships.

    Uses adjacency lists for O(1) neighbor lookup.
    """

    __slots__ = ("_out", "_in", "_symbols", "_edges")

    def __init__(self) -> None:
        self._out: dict[int, list[tuple[int, Edge]]] = {}
        self._in: dict[int, list[tuple[int, Edge]]] = {}
        self._symbols: dict[int, Symbol] = {}
        self._edges: list[Edge] = []

    def add_symbol(self, symbol: Symbol) -> None:
        """Add a symbol node. O(1)."""
        self._symbols[symbol.id] = symbol
        if symbol.id not in self._out:
            self._out[symbol.id] = []
        if symbol.id not in self._in:
            self._in[symbol.id] = []

    def add_edge(self, edge: Edge) -> None:
        """Add a call edge. O(1)."""
        self._edges.append(edge)
        if edge.caller_id not in self._out:
            self._out[edge.caller_id] = []
        if edge.callee_id not in self._in:
            self._in[edge.callee_id] = []
        self._out[edge.caller_id].append((edge.callee_id, edge))
        self._in[edge.callee_id].append((edge.caller_id, edge))

    def get_symbol(self, symbol_id: int) -> Symbol | None:
        """Get symbol by ID. O(1)."""
        return self._symbols.get(symbol_id)

    def get_callees(self, symbol_id: int) -> list[tuple[Symbol, Edge]]:
        """Get direct callees. O(out-degree)."""
        return [
            (self._symbols[cid], edge)
            for cid, edge in self._out.get(symbol_id, [])
            if cid in self._symbols
        ]

    def get_callers(self, symbol_id: int) -> list[tuple[Symbol, Edge]]:
        """Get direct callers. O(in-degree)."""
        return [
            (self._symbols[cid], edge)
            for cid, edge in self._in.get(symbol_id, [])
            if cid in self._symbols
        ]

    def out_degree(self, symbol_id: int) -> int:
        """Number of callees. O(1)."""
        return len(self._out.get(symbol_id, []))

    def in_degree(self, symbol_id: int) -> int:
        """Number of callers. O(1)."""
        return len(self._in.get(symbol_id, []))

    @property
    def num_nodes(self) -> int:
        return len(self._symbols)

    @property
    def num_edges(self) -> int:
        return len(self._edges)

    @property
    def symbols(self) -> dict[int, Symbol]:
        return self._symbols

    def __repr__(self) -> str:
        return f"CallGraph(nodes={self.num_nodes}, edges={self.num_edges})"
