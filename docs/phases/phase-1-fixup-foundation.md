# Phase 1: Fixup & Foundation

## Goal
Eliminate all blockers that would prevent a clean MCP server implementation: fix hardcoded paths, add MCP dependency, and scaffold the empty MCP module.

## Deliverables

### Backend
- [ ] Fix hardcoded `/mnt/raid_0_drive/...` cache_dir default in `src/champi_stt/providers/whisperlive/config.py:62` to `~/.cache/champi-stt/whisper/cache`
- [ ] Fix hardcoded `~/.cache/mcp-champi/transcriptions` references to `~/.cache/champi-stt/transcriptions` in config.py and enums.py
- [ ] Fix hardcoded `mcp_champi` fallback paths in `provider.py` to use `champi-stt` consistently
- [ ] Add `mcp[cli]` to `[project.optional-dependencies]` as a new `mcp` extra group
- [ ] Create empty `src/champi_stt/mcp/__init__.py` module scaffold
- [ ] Update `__version__` from `"0.1.0"` to match project version in `cli.py` (currently hardcoded to 0.1.0 in `@click.version_option`)

### Infrastructure
- [ ] Verify `uv run python -m pytest` still passes after path changes
- [ ] Ensure `uv pip install 'champi-stt[mcp]'` resolves correctly with the new extra

## Done Definition
- `grep -r "/mnt/raid_0_drive" src/` returns zero results
- `grep -r "mcp-champi\|mcp_champi" src/` returns zero results (all replaced with `champi-stt`)
- `uv run python -c "import champi_stt.mcp"` succeeds
- `uv run python -m pytest` passes with no new failures
- `mcp` appears in `pyproject.toml` optional dependencies

## Parallel work
- Path fixes (config.py, enums.py, provider.py) can all be done in one pass
- MCP dependency addition and module scaffold are independent of path fixes

## Phase dependencies
- Requires: none

## Complexity
- Backend: S
- Frontend: N/A
- Infra: S

## Risks
- Path changes could break existing user configs that rely on the old default paths (low risk -- project is pre-v1.0 alpha, no deployed users expected)
