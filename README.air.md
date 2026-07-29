# GOLEM-668 Air-gapped Controller

This branch implements an air-gapped, local-only controller for GOLEM-668 with enhanced features:

- Task metadata (UUID, priority, owner, tags, due, attempts)
- Priority-based queueing and persisted index
- Atomic writes and owner-only file permissions
- Encrypted USB export/import (AES-GCM, PBKDF2) for air-gapped transfers
- CLI for generate|enqueue|list|list-all|process|export-usb|import-usb|show

Security notes:
- No networking code is included. Do not add network transports to this branch.
- The package export uses AES-GCM with a PBKDF2-derived key; share passphrases out-of-band.
- Files are created with owner-only permissions by default (umask set to 0o077).
- For multi-operator environments, perform key exchange via physical handoff or other approved OOB methods.
- When moving packages to/from USB, verify integrity using the tool's import/export process and check logs.

Usage examples:
  python golem668/airgapped_controller.py generate
  python golem668/airgapped_controller.py list
  python golem668/airgapped_controller.py process
  python golem668/airgapped_controller.py export-usb --path /media/usb/golem.pkg
  python golem668/airgapped_controller.py import-usb --path /media/usb/golem.pkg
