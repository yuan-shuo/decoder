"""CLI entry point for Decoder."""

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn

from decoder.core.graph.models import TreeNode
from decoder.core.indexer import Indexer
from decoder.core.models import Edge
from decoder.core.storage import SymbolRepository, get_default_db_path

app = typer.Typer(
    name="decoder",
    help="Static call graph traversal for Python codebases.",
    no_args_is_help=True,
)
console = Console()

_MAX_CONDITION_DISPLAY = 30


def get_repo(path: Path) -> SymbolRepository:
    """Get or create a repository for the given path."""
    db_path = get_default_db_path(path)
    return SymbolRepository(db_path)


def format_context(edge: Edge) -> str:
    """Format edge context as an annotation string."""
    annotations = []

    if edge.is_conditional:
        if edge.condition:
            if len(edge.condition) <= _MAX_CONDITION_DISPLAY:
                cond = edge.condition
            else:
                cond = edge.condition[: _MAX_CONDITION_DISPLAY - 3] + "..."
            annotations.append(f"if {cond}")
        else:
            annotations.append("conditional")

    if edge.is_loop:
        annotations.append("in loop")

    if edge.is_try_block:
        annotations.append("in try")

    if edge.is_except_handler:
        annotations.append("in except")

    if annotations:
        return f"[yellow]\\[{', '.join(annotations)}][/]"
    return ""


@app.command()
def index(
    path: Annotated[Path, typer.Argument(help="Directory to index")] = Path("."),
    force: Annotated[bool, typer.Option("--force", "-f", help="Re-index all files")] = False,
    exclude: Annotated[
        list[str] | None, typer.Option("--exclude", "-e", help="Patterns to exclude")
    ] = None,
) -> None:
    """Index a directory to build the call graph."""
    path = path.resolve()

    with get_repo(path) as repo:
        indexer = Indexer(repo)

        if force:
            repo.clear()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(f"Indexing [cyan]{path.name}[/]", total=None)

            def on_progress(file: Path, current: int, total: int) -> None:
                progress.update(task, total=total, completed=current)
                try:
                    rel_path: Path | str = file.relative_to(path)
                except ValueError:
                    rel_path = file.name
                progress.update(task, description=f"[cyan]{rel_path}[/]")

            stats = indexer.index_directory(
                path, exclude_patterns=exclude or [], force=force, on_progress=on_progress
            )

        console.print("[green]Done![/green]")
        console.print(f"  Files indexed: {stats.files}")
        console.print(f"  Symbols found: {stats.symbols}")
        console.print(f"  Edges created: {stats.edges}")

        if stats.skipped:
            console.print(f"  [dim]Skipped: {stats.skipped}[/]")
        if stats.unchanged:
            console.print(f"  [dim]Unchanged: {stats.unchanged}[/]")
        if stats.errors:
            console.print(f"  [red]Errors: {len(stats.errors)}[/red]")
            for error in stats.errors:
                console.print(f"    {error}")


@app.command()
def stats(
    output_json: Annotated[bool, typer.Option("--json", "-j", help="Output as JSON")] = False,
) -> None:
    """Show index statistics."""
    path = Path(".").resolve()

    with get_repo(path) as repo:
        result = repo.get_stats()

        if output_json:
            print(json.dumps(result))
        else:
            console.print(f"Files indexed: {result['files']}")
            console.print(f"Symbols: {result['symbols']}")
            console.print(f"Edges: {result['edges']}")
            if result["last_indexed"]:
                console.print(f"Last indexed: {result['last_indexed']}")


@app.command()
def find(
    name: Annotated[str, typer.Argument(help="Name to search for")],
    symbol_type: Annotated[
        str | None, typer.Option("--type", "-t", help="Filter by type: function, class, method")
    ] = None,
    output_json: Annotated[bool, typer.Option("--json", "-j", help="Output as JSON")] = False,
) -> None:
    """Search for functions, classes, and methods by name."""
    from decoder.core.models import SymbolType

    path = Path(".").resolve()
    type_filter = SymbolType(symbol_type) if symbol_type else None

    with get_repo(path) as repo:
        symbols = repo.symbols.find(name, type_filter)

        if output_json:
            result = [
                {
                    "id": s.id,
                    "name": s.name,
                    "qualified_name": s.qualified_name,
                    "type": s.type.value,
                    "file": str(s.file),
                    "line": s.line,
                    "end_line": s.end_line,
                }
                for s in symbols
            ]
            print(json.dumps(result))
        else:
            if not symbols:
                console.print(f"No matches for '[cyan]{name}[/cyan]'")
                return
            for symbol in symbols:
                console.print(f"[cyan]{symbol.name}[/cyan] ({symbol.type.value})")
                console.print(f"  {symbol.file}:{symbol.line}")


@app.command()
def callers(
    name: Annotated[str, typer.Argument(help="Function or method name")],
    output_json: Annotated[bool, typer.Option("--json", "-j", help="Output as JSON")] = False,
) -> None:
    """Show what calls a function (who calls this?)."""
    path = Path(".").resolve()

    with get_repo(path) as repo:
        symbols = repo.symbols.find(name)

        if output_json:
            results = []
            for symbol in symbols:
                caller_list = repo.edges.get_callers(symbol.id)
                results.append(
                    {
                        "symbol": {
                            "id": symbol.id,
                            "name": symbol.name,
                            "qualified_name": symbol.qualified_name,
                            "type": symbol.type.value,
                            "file": str(symbol.file),
                            "line": symbol.line,
                            "end_line": symbol.end_line,
                        },
                        "callers": [
                            {
                                "id": caller.id,
                                "name": caller.name,
                                "qualified_name": caller.qualified_name,
                                "type": caller.type.value,
                                "file": str(caller.file),
                                "line": caller.line,
                                "call_line": edge.call_line,
                            }
                            for caller, edge in caller_list
                        ],
                    }
                )
            print(json.dumps(results))
        else:
            if not symbols:
                console.print(f"No matches for '[cyan]{name}[/cyan]'")
                return

            for symbol in symbols:
                console.print(f"\n[bold cyan]{symbol.qualified_name}[/] ({symbol.type.value})")
                console.print(f"  [dim]{symbol.file}:{symbol.line}[/]")

                caller_list = repo.edges.get_callers(symbol.id)
                if not caller_list:
                    console.print("  [dim]No callers found[/]")
                else:
                    console.print("  [green]Called by:[/]")
                    for caller, edge in caller_list:
                        ctx = format_context(edge)
                        ctx_suffix = f" {ctx}" if ctx else ""
                        loc = f"{caller.file}:{edge.call_line}"
                        console.print(f"    [cyan]{caller.name}[/] [dim]({loc})[/]{ctx_suffix}")


@app.command()
def callees(
    name: Annotated[str, typer.Argument(help="Function or method name")],
    output_json: Annotated[bool, typer.Option("--json", "-j", help="Output as JSON")] = False,
) -> None:
    """Show what a function calls (what does this call?)."""
    path = Path(".").resolve()

    with get_repo(path) as repo:
        symbols = repo.symbols.find(name)

        if output_json:
            results = []
            for symbol in symbols:
                callee_list = repo.edges.get_callees(symbol.id)
                results.append(
                    {
                        "symbol": {
                            "id": symbol.id,
                            "name": symbol.name,
                            "qualified_name": symbol.qualified_name,
                            "type": symbol.type.value,
                            "file": str(symbol.file),
                            "line": symbol.line,
                            "end_line": symbol.end_line,
                        },
                        "callees": [
                            {
                                "id": callee.id,
                                "name": callee.name,
                                "qualified_name": callee.qualified_name,
                                "type": callee.type.value,
                                "file": str(callee.file),
                                "line": callee.line,
                                "call_line": edge.call_line,
                            }
                            for callee, edge in callee_list
                        ],
                    }
                )
            print(json.dumps(results))
        else:
            if not symbols:
                console.print(f"No matches for '[cyan]{name}[/cyan]'")
                return

            for symbol in symbols:
                console.print(f"\n[bold cyan]{symbol.qualified_name}[/] ({symbol.type.value})")
                console.print(f"  [dim]{symbol.file}:{symbol.line}[/]")

                callee_list = repo.edges.get_callees(symbol.id)
                if not callee_list:
                    console.print("  [dim]No calls found[/]")
                else:
                    console.print("  [green]Calls:[/]")
                    for callee, edge in callee_list:
                        ctx = format_context(edge)
                        ctx_suffix = f" {ctx}" if ctx else ""
                        line_info = f"[dim](line {edge.call_line})[/]"
                        console.print(f"    [cyan]{callee.name}[/] {line_info}{ctx_suffix}")


@app.command()
def trace(
    name: Annotated[str, typer.Argument(help="Function or method to trace from")],
    max_depth: Annotated[int, typer.Option("--depth", "-d", help="Maximum trace depth")] = 10,
    output_json: Annotated[bool, typer.Option("--json", "-j", help="Output as JSON")] = False,
) -> None:
    """Trace the call as a tree (callers and callees)."""
    from decoder.core.graph import load_from_repository
    from decoder.core.graph.traversal import get_callee_tree, get_caller_tree

    path = Path(".").resolve()

    with get_repo(path) as repo:
        symbols = repo.symbols.find(name)

        if not symbols:
            console.print(f"No matches for '[cyan]{name}[/cyan]'")
            return

        start_symbol = max(
            symbols,
            key=lambda s: len(repo.edges.get_callees(s.id)) + len(repo.edges.get_callers(s.id)),
        )

        graph = load_from_repository(repo)
        callee_tree = get_callee_tree(graph, start_symbol.id, max_depth)
        caller_tree = get_caller_tree(graph, start_symbol.id, max_depth)

        if output_json:

            def tree_to_dict(node: TreeNode, depth: int = 0) -> dict[str, object]:
                return {
                    "name": node.symbol.name,
                    "qualified_name": node.symbol.qualified_name,
                    "type": node.symbol.type.value,
                    "file": str(node.symbol.file),
                    "line": node.symbol.line,
                    "depth": depth,
                    "is_conditional": node.is_conditional,
                    "condition": node.condition,
                    "is_loop": node.is_loop,
                    "is_try_block": node.is_try_block,
                    "children": [tree_to_dict(c, depth + 1) for c in node.children],
                }

            result = {
                "start": start_symbol.qualified_name,
                "callers": tree_to_dict(caller_tree) if caller_tree else None,
                "callees": tree_to_dict(callee_tree) if callee_tree else None,
            }
            print(json.dumps(result))
        else:
            console.print(f"\n[bold]Call tree for [cyan]{start_symbol.name}[/cyan][/]")
            console.print(f"[dim]{start_symbol.file}:{start_symbol.line}[/]\n")

            def format_ctx(node: TreeNode) -> str:
                """Format context annotation."""
                parts = []
                if node.is_conditional:
                    cond = node.condition
                    if cond:
                        if len(cond) > _MAX_CONDITION_DISPLAY:
                            cond = cond[: _MAX_CONDITION_DISPLAY - 3] + "..."
                        parts.append(f"if {cond}")
                    else:
                        parts.append("conditional")
                if node.is_loop:
                    parts.append("loop")
                if node.is_try_block:
                    parts.append("try")
                return f" [yellow]\\[{', '.join(parts)}][/]" if parts else ""

            def get_rel_path(file_path: Path) -> str:
                try:
                    return str(file_path.relative_to(path))
                except ValueError:
                    return file_path.name

            def print_callers(node: TreeNode, prefix: str = "", is_last: bool = True) -> None:
                """Print caller tree (going up)."""
                if not node.children:
                    return
                for i, child in enumerate(node.children):
                    is_child_last = i == len(node.children) - 1
                    # Print children first (outermost callers)
                    print_callers(child, prefix + ("   " if is_last else "│  "), is_child_last)
                    # Then print this caller
                    branch = "└─" if is_child_last else "├─"
                    ctx = format_ctx(child)
                    rel = get_rel_path(child.symbol.file)
                    console.print(
                        f"{prefix}{branch} [blue]{child.symbol.name}[/]{ctx} "
                        f"[dim]{rel}:{child.symbol.line}[/]"
                    )

            def print_callees(
                node: TreeNode, prefix: str = "", is_last: bool = True, skip_root: bool = False
            ) -> None:
                """Print callee tree (going down)."""
                if not skip_root:
                    branch = "└─" if is_last else "├─"
                    ctx = format_ctx(node)
                    rel = get_rel_path(node.symbol.file)
                    console.print(
                        f"{prefix}{branch} [cyan]{node.symbol.name}[/]{ctx} "
                        f"[dim]{rel}:{node.symbol.line}[/]"
                    )
                child_prefix = prefix + ("   " if is_last else "│  ")
                for i, child in enumerate(node.children):
                    is_child_last = i == len(node.children) - 1
                    print_callees(child, child_prefix if not skip_root else prefix, is_child_last)

            if caller_tree and caller_tree.children:
                console.print("[dim]Callers:[/]")
                print_callers(caller_tree)
                console.print()

            console.print(f"[bold yellow]▶ {start_symbol.name}[/] [yellow]◀ selected[/]")
            console.print()

            if callee_tree and callee_tree.children:
                console.print("[dim]Callees:[/]")
                for i, child in enumerate(callee_tree.children):
                    is_last = i == len(callee_tree.children) - 1
                    print_callees(child, "", is_last)

            # Stats
            caller_count = len(list(caller_tree)) - 1 if caller_tree else 0
            callee_count = len(list(callee_tree)) - 1 if callee_tree else 0
            console.print(f"\n[dim]Callers: {caller_count} | Callees: {callee_count}[/]")


if __name__ == "__main__":
    app()
