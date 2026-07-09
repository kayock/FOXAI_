# Living System Scanner

v0.4.0 adds a read-only machine awareness layer.

## API endpoints

```text
http://127.0.0.1:8844/api/system
http://127.0.0.1:8844/api/status
```

## Scanner collects

- Operating system
- Python version
- CPU name and logical cores
- RAM estimate
- GPU names where available
- Disk usage for the KayocktheOS drive
- Git, Node, and npm detection
- Counts for local model and Knowledge files

## Safety

This scanner is read-only.
It does not modify the host machine.
