# mcp-server-decoder

MCP server for [Decoder](https://github.com/maryamtb/decoder), a static call graph analysis for Python codebases. Provides a pre-indexed topoloy for LLMs to use while searching codebases. Unlike `grep`, focused on text matches, decoder navigates call graphs and reduces token usage, while improving latency

### With decoder:
![with-decoder-mcp](./with-decoder.png)

### Without decoder:
![wo-decoder-mcp](./without-decoder.png)

## Usage

## MCP Server

```bash
cd your-project
pip install mcp-server-decoder
decoder index .
claude mcp add decoder -- mcp-server-decoder
```

Verify it's connected. In Claude, run:

```bash
/mcp
# then, "MCP Status"
```

You should see `decoder` listed with its available tools.

### Tools Available

| Tool | Parameters | Description |
|------|------------|-------------|
| `decoder_callers` | `name` | Find what calls a function |
| `decoder_callees` | `name` | Find what a function calls |
| `decoder_trace` | `name`, `max_depth?` | Trace full call tree |
| `decoder_find` | `query`, `type?` | Search for symbols |
| `decoder_stats` | - | View index statistics |