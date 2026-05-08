# Security Policy

## Supported Versions

We release patches for security vulnerabilities in the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 0.2.x   | :white_check_mark: |
| 0.1.x   | :white_check_mark: |
| < 0.1   | :x:                |

## Reporting a Vulnerability

We take the security of Champi STT seriously. If you believe you have found a security vulnerability, please report it to us as described below.

### Reporting Process

**Please do NOT report security vulnerabilities through public GitHub issues.**

Instead, please report them via email to: **oscar.liguori.bagnis@gmail.com**

Include the following information in your report:

- Type of vulnerability (e.g., remote code execution, privilege escalation, data exposure)
- Full paths of source file(s) related to the vulnerability
- Location of the affected source code (tag/branch/commit or direct URL)
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the issue, including how an attacker might exploit it

### Response Timeline

- **Initial Response**: Within 48 hours of report
- **Validation**: Within 7 days
- **Fix Development**: Depends on severity (see below)
- **Public Disclosure**: After patch is released

### Severity Levels

| Severity | Response Time | Public Disclosure |
|----------|---------------|-------------------|
| Critical | 1-3 days      | After patch       |
| High     | 7-14 days     | After patch       |
| Medium   | 30 days       | After patch       |
| Low      | 90 days       | After patch       |

## Security Best Practices

### For Users

#### 1. Keep Software Updated

Always use the latest version of Champi STT:

```bash
uv pip install --upgrade champi-stt
```

#### 2. Secure Configuration

- **Never commit secrets** to version control:
  ```yaml
  # ❌ Bad
  wakeword:
    access_key: "your-secret-key-123"
  ```

- **Use environment variables**:
  ```bash
  export PORCUPINE_ACCESS_KEY="your-secret-key"
  ```

- **Set proper file permissions**:
  ```bash
  chmod 600 ~/.config/champi-stt/assistant_config.yaml
  ```

#### 3. IPC Security

- **Namespace isolation**: Use unique `ipc_memory_prefix` for different applications:
  ```yaml
  ipc:
    memory_prefix: "myapp_assistant"  # Unique prefix
  ```

Clean up orphaned regions:
```bash
champi-stt ipc cleanup
```

Monitor shared memory:
```bash
champi-stt ipc status
```

#### 4. Network Security

- **API endpoints**: Only expose on localhost:
  ```yaml
  commands:
    exact:
      "turn on lights":
        type: "api"
        url: "http://localhost:8080/api/lights/on"  # Use localhost
  ```

- **Use HTTPS** for external APIs:
  ```yaml
  commands:
    exact:
      "check weather":
        type: "api"
        url: "https://api.weather.com/..."  # HTTPS only
  ```

#### 5. Command Execution

- **Validate shell commands**:
  ```yaml
  commands:
    patterns:
      "set volume to (?P<level>\\d+)":  # Validate input with regex
        type: "shell"
        command: "pactl set-sink-volume @DEFAULT_SINK@ {level}%"
  ```

- **Avoid arbitrary code execution**:
  ```yaml
  # ❌ Dangerous - allows arbitrary commands
  commands:
    patterns:
      "run (?P<cmd>.+)":
        type: "shell"
        command: "{cmd}"
  ```

### For Developers

#### 1. Input Validation

Always validate and sanitize user input:

```python
def process_command(command: str) -> None:
    # Validate command against whitelist
    allowed_commands = ["volume", "brightness", "wifi"]

    if not any(cmd in command.lower() for cmd in allowed_commands):
        raise ValueError("Invalid command")

    # Sanitize input
    command = command.strip()
    # ... process command
```

#### 2. Secure IPC

- **Validate struct data**:
  ```python
  def pack_wake_detected(seq_num: int, wake_word: str) -> bytes:
      # Validate inputs
      if not 0 <= seq_num < 2**64:
          raise ValueError("Invalid sequence number")

      # Truncate long strings
      wake_word = wake_word[:MAX_WAKE_WORD_SIZE]

      return WAKE_DETECTED_STRUCT.pack(seq_num, wake_word.encode())
  ```

- **Handle exceptions gracefully**:
  ```python
  try:
      mgr.create_regions()
  except FileExistsError:
      # Clean up orphaned regions
      cleanup_orphaned_regions()
      mgr.create_regions()
  ```

#### 3. Secrets Management

- **Never hardcode secrets**:
  ```python
  # ❌ Bad
  api_key = "sk_live_abcd1234"

  # ✅ Good
  api_key = os.getenv("API_KEY")
  if not api_key:
      raise ValueError("API_KEY environment variable required")
  ```

- **Use secrets detection** (pre-commit hook):
  ```bash
  detect-secrets scan --baseline .secrets.baseline
  ```

#### 4. Dependency Security

List outdated dependencies:
```bash
uv pip list --outdated
```

Upgrade package:
```bash
uv pip install --upgrade <package>
```

Scan with bandit:
```bash
bandit -r src/champi_stt/ --severity-level medium
```

Scan for secrets:
```bash
detect-secrets scan
```

#### 5. Error Handling

- **Don't leak sensitive info** in errors:
  ```python
  # ❌ Bad - leaks path info
  raise ValueError(f"Failed to load config from {config_path}")

  # ✅ Good - generic error
  logger.error(f"Failed to load config from {config_path}")
  raise ValueError("Failed to load configuration")
  ```

## Pre-release Security Audit (v0.2.0)

A bandit audit at LOW severity was run against `src/champi_stt/` prior to the
v0.2.0 release. Findings and dispositions:

| ID | Severity | Location | Disposition |
|---|---|---|---|
| B602 | High | `assistant/commands/builtin.py:125` | Fixed — replaced `shell=True` with explicit `["cmd", "/c", "start", "", app_name]` list |
| B324 | High | `providers/whisperlive/models.py:121` | Fixed — added `usedforsecurity=False` to `hashlib.md5()` cache-key call |
| B301 | Medium | `assistant/speaker.py:76` | Accepted with `# nosec B301` — pickle reads files written by this application only, not external input |

Remaining LOW findings (49 total) are primarily `assert` statements in tests and
subprocess calls with validated, non-user-supplied arguments. None represent
exploitable attack surface in normal deployment.

## Known Security Considerations

### Shared Memory (IPC)

**Consideration**: Shared memory is accessible to all processes with appropriate permissions.

**Mitigation**:
- Use unique namespace prefixes (`ipc_memory_prefix`)
- Clean up orphaned regions regularly
- Run assistant with least privilege

### Voice Command Execution

**Consideration**: Voice commands can execute shell commands or API calls.

**Mitigation**:
- Whitelist allowed commands
- Validate all inputs with regex patterns
- Use parameter sanitization
- Log all executed commands

### Wake Word Audio Processing

**Consideration**: Microphone access could potentially be abused.

**Mitigation**:
- Audio is processed locally (no cloud transmission)
- Clear visual indicators when recording (wake indicator UI)
- User controls via wake words

### Network Requests

**Consideration**: Commands can make HTTP requests.

**Mitigation**:
- Only allow HTTPS for external APIs
- Validate URLs before making requests
- Implement request timeouts
- Log all network activity

## Security Checklist

Before deploying Champi STT:

- [ ] All secrets moved to environment variables
- [ ] Configuration files have restricted permissions (600)
- [ ] IPC namespace is unique to your application
- [ ] Shell commands are validated and whitelisted
- [ ] Network requests use HTTPS
- [ ] Latest version installed
- [ ] Pre-commit security hooks enabled
- [ ] Orphaned memory regions cleaned up

## Security Tools

### Pre-commit Hooks

Install pre-commit:
```bash
pre-commit install
```

Run all hooks manually:
```bash
pre-commit run --all-files
```

Includes:
- `detect-secrets` - Secrets detection
- `bandit` - Security linting
- `ruff` - Code quality

### Manual Security Scan

Security audit:
```bash
bandit -r src/champi_stt/ -f json -o security-report.json
```

Secrets scan:
```bash
detect-secrets scan --baseline .secrets.baseline
```

## Compliance

### Data Privacy

- **No cloud processing**: All STT processing is local (faster-whisper)
- **No telemetry**: No usage data collected by default
- **User data**: Audio is processed in memory, not stored

### GDPR Considerations

If using speaker identification:
- Inform users about voice data processing
- Provide data deletion mechanism (`champi-stt speaker remove <name>`)
- Secure storage of voice embeddings

## Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Python Security Best Practices](https://python.readthedocs.io/en/stable/library/security_warnings.html)
- [Shared Memory Security](https://docs.python.org/3/library/multiprocessing.shared_memory.html)

## Questions?

For security-related questions (non-vulnerabilities), please open a GitHub Discussion or contact: oscar.liguori.bagnis@gmail.com
