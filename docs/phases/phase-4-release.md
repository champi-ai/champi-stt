# Phase 4: Release Prep & Publish

## Goal
champi-stt v1.0.0 is published to PyPI with all extras installable, migration guide written, and release announcement ready.

## Deliverables

### Backend
- [ ] Bump version to `1.0.0` in `pyproject.toml` and `src/champi_stt/__init__.py`
- [ ] Update `Development Status` classifier from `3 - Alpha` to `5 - Production/Stable`
- [ ] Verify all optional extras install cleanly: `pip install 'champi-stt[mcp]'`, `'champi-stt[all]'` (addresses issue #31)
- [ ] Add `mcp` extra to the `all` extras group in pyproject.toml
- [ ] Final pass: ensure no hardcoded dev paths, no debug prints, no TODO comments in MCP module

### Infrastructure
- [ ] Run `uv build` and verify wheel/sdist contents include `champi_stt/mcp/`
- [ ] Test install from built wheel in a clean virtualenv
- [ ] Publish to TestPyPI first, verify install matrix across Python 3.12
- [ ] Publish to PyPI via `uv publish` or GitHub release workflow
- [ ] Create GitHub release with changelog

### Documentation
- [ ] Write v1.0.0 migration guide (`docs/migration-v1.0.md`) (addresses issue #32)
- [ ] Write release announcement for issue #32
- [ ] Update README with MCP server usage section
- [ ] Ensure `champi-stt mcp serve --help` output is clear and complete

## Done Definition
- `pip install champi-stt[mcp]` from PyPI succeeds in a fresh virtualenv
- `pip install champi-stt[all]` from PyPI succeeds and includes MCP
- `champi-stt mcp serve` works after PyPI install
- v1.0.0 tag exists on GitHub with release notes
- Migration guide exists at `docs/migration-v1.0.md`
- Issues #31 and #32 can be closed

## Parallel work
- Migration guide writing can happen alongside PyPI publish testing
- README updates can happen alongside TestPyPI verification

## Phase dependencies
- Requires: Phase 3 (tests passing, coverage acceptable)

## Complexity
- Backend: S
- Frontend: N/A
- Infra: M

## Risks
- Optional dependency resolution conflicts on PyPI (especially torch extras with platform-specific wheels)
- TestPyPI may have missing transitive dependencies
- Release workflow may need manual intervention if commitizen bump has issues
