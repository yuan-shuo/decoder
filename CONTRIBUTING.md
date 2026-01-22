# Contributing

Hey, thank you for your interest in contributing! Feedback, bug reports, and PRs are welcome. If you have any questions or ideas, feel free to open a [GitHub issue](https://github.com/maryamtb/decoder/issues).

## Getting Started

```bash
git clone https://github.com/maryamtb/decoder.git
cd decoder
uv sync
```

## Running Tests

```bash
uv run pytest           
uv run pytest tests/unit         
uv run pytest tests/integration  
```

## Lint and Type Checking

```bash
uv run ruff check .    
uv run ruff format .   
uv run mypy decoder/   
```

## Testing the CLI

```bash
uv run decoder index .
uv run decoder trace main
uv run decoder callers <function_name>
uv run decoder callees <function_name>
```
