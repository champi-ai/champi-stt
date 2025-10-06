# Dependencies Validation Report

**Date**: 2025-10-01
**Status**: ✅ **ALL DEPENDENCIES COPIED SUCCESSFULLY**

---

## Validation Summary

🎉 **ALL CHECKS PASSED (8/8)**

---

## 1️⃣ Main Dependencies

| Metric | Count |
|--------|-------|
| Champi dependencies | 50 |
| Champi-STT dependencies | 54 |
| Missing from STT | **0** ✅ |
| STT-specific additions | 4 |

### All 50 Champi Dependencies Copied ✅

1. uv
2. fastmcp
3. numpy
4. sounddevice
5. scipy
6. pydub
7. simpleaudio
8. httpx
9. webrtcvad
10. unidecode
11. espeak-phonemizer
12. tiktoken
13. loguru
14. openai
15. matplotlib
16. mutagen
17. psutil
18. espeakng-loader
19. kokoro
20. misaki[en,ja,ko,zh]
21. spacy
22. en-core-web-sm (spacy model)
23. inflect
24. phonemizer-fork
25. av
26. text2num
27. soundfile
28. aiofiles
29. tqdm
30. mcp[cli]
31. faster-whisper
32. ctranslate2
33. tokenizers
34. onnxruntime
35. imgui-bundle
36. pyglm
37. uv-build>=0.7.21
38. vulture>=2.14
39. torch
40. torchaudio
41. blinker>=1.9.0
42. awaitlet>=0.0.1
43. rich>=14.0.0
44. prompt-toolkit>=3.0.52
45. typer>=0.16.0
46. pypdf2>=3.0.1
47. beautifulsoup4>=4.13.5
48. requests>=2.28.1
49. textual>=5.3.0
50. champi-signals

### STT-Specific Additions (4)

These are additional dependencies required specifically for champi-stt:

1. **librosa>=0.10.0** - Audio analysis library
2. **click>=8.0.0** - CLI framework
3. **pyyaml>=6.0.0** - YAML configuration
4. **aiohttp>=3.8.0** - Async HTTP client

---

## 2️⃣ Optional Dependencies

### Dev Dependencies ✅

All 8 champi dev dependencies present, plus additional tooling:

**From Champi:**
- build
- twine
- pytest
- pytest-asyncio
- pytest-cov
- pytest-mock
- pre-commit
- ruff

**Additional in STT:**
- black>=23.0.0
- mypy>=1.0.0
- bandit[toml]>=1.7.0
- detect-secrets>=1.4.0

### Test Dependencies ✅

All 4 test dependencies match exactly:
- pytest
- pytest-asyncio
- pytest-cov
- pytest-mock

---

## 3️⃣ Tool Configurations

All tool configurations from champi have been copied:

| Configuration | Status |
|--------------|--------|
| Ruff | ✅ Copied |
| Pytest | ✅ Copied |
| Scripts (security, lint, format, test) | ✅ Copied |
| UV | ✅ Copied |
| Black | ✅ Added |
| MyPy | ✅ Added |
| Bandit | ✅ Added |

---

## 4️⃣ Special Configurations

### UV Configuration ✅
```toml
[tool.uv]
package = true
no-build-isolation = false
managed = true

[tool.uv.sources]
champi-signals = { path = "../champi_signals/dist/champi_signals-0.1.0-py3-none-any.whl" }
```

### PyTorch CUDA Index ✅
```toml
[[tool.uv.index]]
url = "https://download.pytorch.org/whl/cu129"
```

### Tool Scripts ✅
```toml
[tool.scripts]
security = ["bandit -r src/champi_stt/ --severity-level medium", "./gitleaks detect --source . --verbose"]
security-full = ["bandit -r src/champi_stt/ -f json", "./gitleaks detect --source . --verbose"]
lint = "ruff check src/champi_stt/"
format = "ruff format src/champi_stt/"
test = "pytest tests/"
clean-security = "rm -f gitleaks.tar.gz && rm -f gitleaks"
```

---

## 5️⃣ Ruff Configuration Details

Complete champi ruff configuration copied:

- **Line length**: 88 (matching champi)
- **Target version**: py312
- **Indent width**: 4
- **Select rules**: E, W, F, UP, B, SIM, I, N, C90, RUF
- **Ignore rules**: E501, B008, C901, RUF012
- **Format style**: Double quotes, spaces, auto line endings
- **Per-file ignores**: Test files with S101, ARG, FBT, PLR2004, S311

---

## 6️⃣ Dependency Groups

```toml
[dependency-groups]
dev = ["bandit>=1.8.6"]
```

---

## Conclusion

✅ **VALIDATION SUCCESSFUL**

All dependencies, configurations, and tool setups from champi have been successfully copied to champi_stt. The library maintains full compatibility with the champi ecosystem while adding STT-specific enhancements.

**Total Items Validated**: 8/8 ✅
- Main dependencies: 50/50 ✅
- Dev dependencies: 8/8 ✅
- Test dependencies: 4/4 ✅
- Tool configurations: All present ✅
- UV setup: Complete ✅
- PyTorch CUDA: Configured ✅
- Scripts: All copied ✅
