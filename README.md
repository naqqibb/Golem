# Golem

Techne Enhanced Systems in Matrix STS — cryptographic ethnography for steganographic variables in systems science

## Ethnography of Hidden Variables

Golem treats steganographic variables not as opaque payloads but as cultural artifacts inside computational ecologies. Each variable carries provenance, intent, and ritual: how it was generated, who encoded it, and how it travels through systems. This README frames methods as ethnographic field notes for engineers who want to treat secrecy, embedding, and signal shaping as disciplined systems-science practice rather than scattered tooling.

## Principles

- Observe before encoding: characterize the carrier, its transformations, and the socio-technical context that shapes detectability.
- Variables as symbols: name and model each stego-variable with metadata (origin, entropy, sensitivity, expected transformations).
- Minimal revelation: design encodings to preserve the host's behavioral norms so signals remain endemic, not foreign.
- Auditability over opacity: prefer cryptographic proofs and provenance markers you can inspect, not magic black boxes.

## Steganographic Variable Model

A stego-variable in Golem is defined by a small JSON manifest attached to the payload:

- id: opaque identifier (UUID v4)
- schema: domain and meaning (e.g., "economic:flow_rate")
- entropy: bits of randomness measured and recorded
- cipher: algorithm used (AES-GCM, ChaCha20-Poly1305)
- transform: expected carrier operations (resize, recompress, resample)
- provenance: signer fingerprint and timestamp

Model example (conceptual):

```json
{
  "id": "b9a1f3e2-...",
  "schema": "signals.phase.shift",
  "entropy": 128,
  "cipher": "AES-GCM",
  "transform": ["jpeg:quality:85","resize:down:0.5"],
  "provenance": "did:example:alice#key"
}
```

## Workflows (systems-science posture)

1. Ethnographic survey: map carriers and stakeholders; note automatic processing pipelines.
2. Encode with resilience: choose transforms and adaptive capacity to survive expected noise.
3. Test under sociotechnical stress: run simulated pipelines, record detection metrics, and update the manifest.
4. Institutionalize: document embed/unwrap rituals and key-management policies so signals remain interpretable across teams.

## Practical snippets

- Use authenticated encryption (AEAD) for payloads.
- Attach a short, versioned manifest to every stego-variable so downstream systems can reason about it.

Minimal Python sketch (illustrative):

```python
from uuid import uuid4
from datetime import datetime

manifest = {
    "id": str(uuid4()),
    "schema": "signals.phase.shift",
    "entropy": 128,
    "cipher": "AES-GCM",
    "transform": ["jpeg:quality:85"],
    "provenance": "naqqibb"
}

# serialize guard and encrypt payload with AEAD; embed following carrier norms
```

## Ethics, Legality, and Openness

Treat steganographic practice as a socio-technical discipline. Obtain consent, evaluate legal constraints in your jurisdiction, and prefer transparent provenance that allows later audit.

## References & Further Thought

This project is a conceptual toolbox: combine cryptographic rigor with ethnographic methods to design hardy, interpretable steganographic variables embedded within living systems.
