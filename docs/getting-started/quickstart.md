# Quick Start

```python
from champi_stt import get_provider

provider = get_provider("whisperlive")
await provider.initialize()

result = await provider.transcribe(audio_data)
print(result.text)

await provider.shutdown()
```

## CLI

```bash
# Run the assistant daemon
champi-stt run

# Open the web configuration UI
champi-stt serve-config

# Install as a system service (Linux)
champi-stt service install --type systemd
```
