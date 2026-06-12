# Migrating to champi-stt v1.0.0

This guide covers everything you need to know when upgrading from any pre-1.0 build of champi-stt.

---

## What changed in v1.0.0

| Area | Change |
|---|---|
| Cache directory | Renamed from `~/.cache/mcp-champi/` to `~/.cache/champi-stt/` |
| MCP server | New feature: expose transcription tools over the Model Context Protocol |
| Version string | `champi-stt --version` now reports the actual package version |
| Public API | Stable semver guarantee begins — breaking changes will require a major bump |
| Test coverage | CI coverage threshold enforced at 55% |

---

## Cache directory changes

Pre-1.0 builds wrote data to paths containing the old package name `mcp-champi`:

```
~/.cache/mcp-champi/transcriptions/
~/.cache/mcp-champi/whisper/cache/
```

From v1.0.0 onward all data is written under `champi-stt`:

```
~/.cache/champi-stt/transcriptions/
~/.cache/champi-stt/whisper/cache/
```

### Manual migration

If you have existing transcription cache files you want to preserve, move them once before starting v1.0.0 for the first time:

```bash
# Transcription cache
mv ~/.cache/mcp-champi/transcriptions ~/.cache/champi-stt/transcriptions

# WhisperLive model cache
mkdir -p ~/.cache/champi-stt/whisper
mv ~/.cache/mcp-champi/whisper/cache ~/.cache/champi-stt/whisper/cache

# Remove the old top-level directory when you are satisfied
rmdir ~/.cache/mcp-champi 2>/dev/null || rm -rf ~/.cache/mcp-champi
```

If you do not migrate, champi-stt will simply create a fresh cache directory the first time it runs. Cached transcriptions from pre-1.0 will not be picked up, but no data is deleted automatically.

### Custom cache directory

If you were overriding the cache directory with the `CHAMPI_CACHE_DIR` environment variable or `cache_dir` in your config, no change is needed — your override continues to take effect.

---

## MCP server (new in v1.0.0)

The v1.0.0 release ships an [MCP](https://modelcontextprotocol.io/) server that lets LLM hosts such as Claude Desktop call champi-stt transcription tools directly.

### Install

The MCP server is shipped as an optional extra. Download the wheel from the [v1.0.0 GitHub Release](https://github.com/champi-ai/champi-stt/releases/tag/v1.0.0) and install it with the `mcp` extra:

```bash
pip install "champi_stt-1.0.0-py3-none-any.whl[mcp]"
```

Or, if you manage the project with `uv`:

```bash
uv pip install "champi_stt-1.0.0-py3-none-any.whl[mcp]"
```

To include all optional extras at once:

```bash
pip install "champi_stt-1.0.0-py3-none-any.whl[all]"
```

### Start the server

```bash
champi-stt mcp serve
```

Run with `--help` to see all options (including SSE transport):

```bash
champi-stt mcp serve --help
```

### Register with Claude Desktop

Add a server entry to your `claude_desktop_config.json`:

- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "champi-stt": {
      "command": "champi-stt-mcp"
    }
  }
}
```

To select a non-default STT provider:

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

Restart Claude Desktop after editing the file.

### Available MCP tools

| Tool | Description |
|---|---|
| `list_providers` | Return the names of all registered STT providers |
| `get_provider_status` | Return health and model information for a named provider |
| `transcribe_audio` | Transcribe a local audio file and return the transcript text |
| `detect_language` | Detect the spoken language in a local audio file |

For full setup and smoke-test instructions see [docs/mcp-integration.md](mcp-integration.md).

---

## Version string fix

Before v1.0.0, `champi-stt --version` printed a hardcoded `0.1.0` regardless of the installed version. This is now fixed — the version is read from the package metadata at runtime:

```bash
champi-stt --version
# champi-stt, version 1.0.0
```

---

## Stable public API

Starting with v1.0.0 the following symbols form the stable public API surface. Breaking changes to these will require a major version bump:

- `get_provider(provider_type, config, **kwargs) -> BaseSTTProvider`
- `get_default_provider() -> BaseSTTProvider`
- `list_providers() -> list[str]`
- `BaseSTTProvider`, `BaseSTTConfig`, `BaseTranscriber`, `BaseModelManager`
- `TranscriptionResponse`, `TranscriptionSegment`
- `STTResponse` (alias, kept for backward compatibility)

Everything else is considered internal and may change between minor releases.

---

## Minimum requirements

- Python 3.12 or later (unchanged from pre-1.0)
- No new mandatory runtime dependencies compared with 0.2.0

---

## Release announcement

### champi-stt v1.0.0

We are happy to announce the first stable release of **champi-stt**.

**Highlights:**

- **Stable API.** The core factory and provider interfaces are now under a semantic versioning guarantee. You can depend on `champi-stt >=1.0,<2.0` without worrying about surprise breakage.
- **MCP server.** A new `mcp` optional extra ships a full [Model Context Protocol](https://modelcontextprotocol.io/) server. LLM hosts such as Claude Desktop can now call `transcribe_audio`, `detect_language`, `list_providers`, and `get_provider_status` directly over stdio or SSE — no custom glue code required.
- **Clean paths.** All cache and data directories previously written under `~/.cache/mcp-champi/` have moved to `~/.cache/champi-stt/`. The old hardcoded development paths are gone.
- **Correct version string.** `champi-stt --version` now reports the real installed version instead of the stale `0.1.0` placeholder.
- **Test coverage enforced.** CI now requires 55% line coverage and runs a dedicated MCP server startup integration test.

**Install from the GitHub Release asset:**

```bash
pip install "champi_stt-1.0.0-py3-none-any.whl"
# or with MCP support
pip install "champi_stt-1.0.0-py3-none-any.whl[mcp]"
```

See the [migration guide](docs/migration-v1.0.md) for upgrade instructions.
