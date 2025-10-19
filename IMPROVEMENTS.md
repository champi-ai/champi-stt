# Comprehensive Improvement Plan for champi-stt
*(Excluding OpenWakeWordDetector implementation)*

## 🔴 **Critical Bugs** (Fix Immediately)

### 1. Fix Broken Test Imports
**Issue**: `test_wakeword.py:13` imports non-existent `PorcupineDetector`
- **Impact**: Tests fail immediately on import
- **Solution**: Remove or update tests to use actual implementations (Whisper)

### 2. Fix IPC Config Loading Bug
**Issue**: Example config has `ipc:` top-level key, but `from_dict()` reads from `service_config`
- **Files**: `assistant_config.yaml` uses `ipc:`, but `config.py:134-137` reads `service_config.get("ipc_*")`
- **Impact**: IPC settings silently ignored, defaults always used
- **Solution**: Add `ipc_config = config_dict.get("ipc", {})` and read from there

### 3. Fix Missing CLI Import
**Issue**: `cli.py:101` uses undefined `OpenWakeWordDetector`
- **Impact**: Assistant start command crashes
- **Solution**: Add proper import handling or use WhisperWakeWordDetector as fallback

---

## 🟡 **High Priority** (Missing Features)

### 4. Add Comprehensive IPC Tests
**Gap**: Zero test coverage for IPC system
- Create `tests/test_ipc_shared_memory.py` - Memory manager lifecycle tests
- Create `tests/test_ipc_signal_processor.py` - Signal processing tests
- Create `tests/test_ipc_signal_reader.py` - Signal reading tests
- Create `tests/test_ipc_integration.py` - End-to-end IPC tests

### 5. Integrate cleanup_orphaned_regions
**Gap**: Function exists but never called
- Add cleanup call in daemon startup (before creating regions)
- Add cleanup in daemon shutdown (optional, for safety)
- Create CLI command: `champi-stt ipc cleanup`

### 6. Add IPC CLI Commands
Create `ipc` command group:
```bash
champi-stt ipc cleanup              # Clean orphaned memory
champi-stt ipc status               # Show memory regions
champi-stt ipc test-ui [--prefix]   # Launch test UI standalone
```

### 7. Add CONTRIBUTING.md
Include development setup, code style, testing requirements, PR process

### 8. Add SECURITY.md
Include vulnerability reporting, supported versions, security best practices

---

## 🟢 **Medium Priority** (Quality Improvements)

### 9. Improve Type Hints Coverage
- Add return type annotations to all public functions
- Add type hints to `data_mapper` callbacks
- Use `typing.Protocol` for callback types

### 10. Enhance Error Handling
- Add try-except in IPC signal processor loop
- Add retry logic for shared memory attach failures
- Improve error messages with actionable solutions

### 11. Add Integration Tests
Create `tests/integration/` with full workflow tests

### 12. Complete Module Documentation
- Add module-level docstrings to all files
- Document all public classes with usage examples

---

## 🔵 **Low Priority** (Nice to Have)

### 13. Performance Optimizations
- Profile IPC signal latency
- Optimize struct packing/unpacking
- Add benchmarking suite

### 14. Enhanced CLI Features
```bash
champi-stt assistant status
champi-stt assistant logs [--tail]
champi-stt config validate FILE
```

### 15. Improve Developer Experience
- Add `.editorconfig`, VS Code settings, Makefile

### 16. Enhanced Documentation
- Add troubleshooting guide, video tutorials, architecture diagrams

---

## 📋 **Execution Order**

**Phase 1 - Critical Fixes** (1 day)
1. Fix test imports
2. Fix IPC config loading
3. Fix CLI import

**Phase 2 - Core Features** (3-4 days)
4. Add IPC tests
5. Integrate cleanup utilities
6. Add IPC CLI commands
7. Add CONTRIBUTING.md and SECURITY.md

**Phase 3 - Quality** (3-5 days)
8. Improve type hints
9. Enhance error handling
10. Add integration tests
11. Complete documentation

**Phase 4 - Polish** (ongoing)
12. Performance optimizations
13. Enhanced CLI features
14. Developer experience
15. Expanded documentation

---

## 🎯 **Success Metrics**

- ✅ All tests passing (100% critical path coverage)
- ✅ Type hints coverage >90%
- ✅ Zero critical bugs in issue tracker
- ✅ CI/CD pipeline green
- ✅ Documentation complete and accurate
- ✅ IPC latency <1ms (p95)
- ✅ No config loading issues
- ✅ Clean `mypy --strict` run