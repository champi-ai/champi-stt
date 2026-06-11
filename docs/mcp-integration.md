# MCP Integration

Champi STT exposes speech-to-text capabilities over the
[Model Context Protocol (MCP)](https://modelcontextprotocol.io/), letting
LLM hosts such as Claude Desktop call transcription tools directly via stdio.

## Prerequisites

Install the `mcp` optional extra:

```bash
pip install "champi-stt[mcp]"
```

## Claude Desktop Setup

Add a server entry to your `claude_desktop_config.json`:

- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

### Production (installed package)

```json
{
  "mcpServers": {
    "champi-stt": {
      "command": "champi-stt-mcp"
    }
  }
}
```

### Development (`uv run`)

Use this form when working directly from a source checkout:

```json
{
  "mcpServers": {
    "champi-stt": {
      "command": "uv",
      "args": ["run", "champi-stt", "mcp", "serve"],
      "cwd": "/path/to/champi-stt"
    }
  }
}
```

Replace `/path/to/champi-stt` with the absolute path to your local clone.

### With environment variables

Pass `CHAMPI_STT_PROVIDER` to select a non-default provider:

```json
{
  "mcpServers": {
    "champi-stt": {
      "command": "champi-stt-mcp",
      "env": {
        "CHAMPI_STT_PROVIDER": "whisperlive"
      }
    }
  }
}
```

After editing the file, restart Claude Desktop for the change to take effect.

## Smoke-test

Verify the stdio handshake without a full MCP client by piping an
`initialize` request directly to the server:

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"0.1"}}}' \
  | champi-stt mcp serve 2>/dev/null
```

Expected output: a JSON-RPC response whose `"result"` contains `serverInfo`:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2024-11-05",
    "serverInfo": {
      "name": "champi-stt",
      "version": "0.2.0"
    },
    "capabilities": {}
  }
}
```

The `2>/dev/null` suppresses loguru startup output which is written to stderr
and never touches the JSON-RPC stream.

## Available Tools

| Tool | Description |
|---|---|
| `list_providers` | Return the names of all registered STT providers |
| `get_provider_status` | Return health and model information for a named provider |
| `transcribe_audio` | Transcribe a local audio file and return the transcript text |
| `detect_language` | Detect the spoken language in a local audio file |

## SSE Transport

For non-Claude-Desktop clients that prefer HTTP/SSE over stdio:

```bash
champi-stt mcp serve --transport sse --port 8765
```

Connect your MCP client to `http://localhost:8765/sse`.
