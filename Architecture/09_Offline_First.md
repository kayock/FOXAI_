# Offline-First Policy

FOXAI is USB-first and should remain useful without Internet access.

## Rule

Every subsystem must answer:

Can this work offline?

If not, it must degrade gracefully.

## Preferred Resources

- Local GGUF models
- Local documentation
- Kiwix archives
- SQLite databases
- Local vector indexes
- Local mission history
- Local configuration

## Online Features

Online tools are allowed only as optional providers.
The offline path must remain stable.
