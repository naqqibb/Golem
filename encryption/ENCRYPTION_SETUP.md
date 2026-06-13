# Golem Encrypted Asset Storage - Setup Guide

## Overview

This document provides complete setup instructions for AES-256-GCM encrypted asset storage in the Golem repository with secure regional distribution via API endpoints.

## Security Specifications

### Encryption Parameters
- **Algorithm**: AES-256-GCM (Galois/Counter Mode)
- **Key Size**: 256 bits (32 bytes)
- **Key Derivation**: PBKDF2-SHA256 with 100,000 iterations
- **IV Length**: 12 bytes (96 bits)
- **Authentication Tag**: 16 bytes (128 bits)
- **Salt Length**: 16 bytes (128 bits)

### Authentication & Integrity
- GCM provides built-in authentication
- Tampering is automatically detected during decryption
- Authentication tag validates both ciphertext and metadata

### Transit Security
- **Protocol**: TLS 1.2+ (enforced)
- **Certificate Validation**: Required
- **Retry Policy**: 3 attempts with exponential backoff (0.5s base)
- **Timeout**: 30 seconds per request

## Prerequisites

- Python 3.9+
- `cryptography` library (>=41.0.0)
- `requests` library (>=2.31.0)
- GitHub repository with Actions enabled
- Admin access to repository settings

## Step-by-Step Setup

### 1. Generate Master Encryption Key

```bash
# Generate cryptographically secure 256-bit key
python3 -c "import os; key = os.urandom(32); print(key.hex())"
```

**Output example**: `a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2`

**⚠️ CRITICAL**: Save this key securely. You will need it to add to GitHub Secrets.

### 2. Configure GitHub Secrets

1. Go to your repository: https://github.com/naqqibb/Golem
2. Navigate to: **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret** and add the following:

#### Required Secrets

| Secret Name | Value | Description |
|-------------|-------|-------------|
| `MASTER_ENCRYPTION_KEY` | Your 256-bit hex key | Master key for AES-256-GCM encryption |
| `GOLEM_API_KEY` | Your Golem API key | Authentication for Golem API |
| `GOLEM_API_SECRET` | Your Golem API secret | Secret for Golem API authentication |
| `GOLEM_API_EAST_1` | `https://api-east-1.golem.example.com` | Eastern region 1 endpoint |
| `GOLEM_API_EAST_2` | `https://api-east-2.golem.example.com` | Eastern region 2 endpoint |

**Adding Secrets**:
```
1. Secret name: MASTER_ENCRYPTION_KEY
   Value: <your-hex-key>
   
2. Secret name: GOLEM_API_KEY
   Value: <your-api-key>
   
3. Secret name: GOLEM_API_SECRET
   Value: <your-api-secret>
   
4. Secret name: GOLEM_API_EAST_1
   Value: https://api-east-1.golem.network/v1
   
5. Secret name: GOLEM_API_EAST_2
   Value: https://api-east-2.golem.network/v1
```

### 3. Create Assets Directory

```bash
# Create directory for assets to encrypt
mkdir -p assets

# Example: Add an agent model or configuration
cp /path/to/your/agent_model.bin assets/
cp /path/to/your/config.json assets/
```

### 4. Verify Installation

```bash
# Install dependencies
pip install cryptography requests

# Test encryption locally
python3 << 'EOF'
import sys
sys.path.insert(0, 'encryption')
from asset_encryption import GolemAssetEncryption

# Create test encryptor
test_key = "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2"
encryptor = GolemAssetEncryption(test_key)

# Encrypt test data
test_data = b"Hello, Golem!"
encrypted = encryptor.encrypt_asset(test_data, region='east-1')
print(f"✓ Encryption successful")
print(f"  Algorithm: {encrypted['algorithm']}")
print(f"  Region: {encrypted['region']}")

# Decrypt to verify
decrypted = encryptor.decrypt_asset(encrypted)
assert decrypted == test_data, "Decryption failed!"
print(f"✓ Decryption verified")
EOF
```

### 5. Deploy Assets

```bash
# Add encrypted assets to repository
git add assets/
git add encryption/
git add .github/workflows/encrypt-deploy.yml

# Commit changes
git commit -m "chore: Add encrypted asset storage infrastructure"

# Push to trigger GitHub Actions
git push origin main
```

### 6. Monitor Deployment

1. Go to: **Actions** → **Encrypt & Deploy Assets to Golem**
2. Watch the workflow run for both regions (east-1, east-2)
3. Check logs for:
   - `✓ Encrypted: assets/...` (successful encryption)
   - `✓ Deployment successful` (API upload)
   - Audit log with timestamp and commit SHA

## Usage Examples

### Local Encryption

```python
from encryption.asset_encryption import GolemAssetEncryption
import os

# Load master key from environment
master_key = os.getenv('MASTER_ENCRYPTION_KEY')
encryptor = GolemAssetEncryption(master_key)

# Encrypt file
with open('assets/agent_model.bin', 'rb') as f:
    data = f.read()

encrypted = encryptor.encrypt_asset(
    data,
    region='east-1',
    metadata={'version': '1.0', 'type': 'agent'}
)

print(f"Ciphertext length: {len(encrypted['ciphertext'])} bytes")
print(f"Region: {encrypted['region']}")
print(f"Algorithm: {encrypted['algorithm']}")
```

### Send to Golem API

```python
from encryption.api_client import GolemRegionalAPIClient
import os

master_key = os.getenv('MASTER_ENCRYPTION_KEY')
client = GolemRegionalAPIClient(master_key, region='east-1')

# Send encrypted asset
with open('assets/config.json', 'rb') as f:
    data = f.read()

result = client.send_encrypted_asset(
    data,
    asset_name='config',
    metadata={'env': 'production'}
)

if result['success']:
    print(f"✓ Asset uploaded to {result['region']}")
else:
    print(f"✗ Upload failed: {result['error']}")
```

### Retrieve & Decrypt

```python
from encryption.api_client import GolemRegionalAPIClient
import os

master_key = os.getenv('MASTER_ENCRYPTION_KEY')
client = GolemRegionalAPIClient(master_key, region='east-1')

# Retrieve asset
result = client.retrieve_encrypted_asset('asset_id_xyz')

if result['success']:
    decrypted_data = result['data']
    print(f"✓ Asset retrieved from {result['region']}")
    print(f"  Data length: {len(decrypted_data)} bytes")
else:
    print(f"✗ Retrieval failed: {result['error']}")
```

## Key Rotation Procedure

### When to Rotate
- Every 90 days (security best practice)
- Immediately if key is compromised
- When team member with access leaves

### Rotation Steps

1. **Generate new master key**
   ```bash
   python3 -c "import os; print(os.urandom(32).hex())"
   ```

2. **Re-encrypt all assets**
   ```bash
   python3 << 'EOF'
   import sys
   import os
   import json
   sys.path.insert(0, 'encryption')
   from asset_encryption import GolemAssetEncryption
   
   old_key = os.getenv('OLD_MASTER_KEY')
   new_key = os.getenv('NEW_MASTER_KEY')
   
   old_encryptor = GolemAssetEncryption(old_key)
   new_encryptor = GolemAssetEncryption(new_key)
   
   # Decrypt with old key, encrypt with new key
   for filename in os.listdir('assets'):
     if filename.endswith('.encrypted'):
       with open(f'assets/{filename}', 'r') as f:
         encrypted_old = json.load(f)
       
       decrypted = old_encryptor.decrypt_asset(encrypted_old)
       encrypted_new = new_encryptor.encrypt_asset(decrypted, region=encrypted_old['region'])
       
       with open(f'assets/{filename}', 'w') as f:
         json.dump(encrypted_new, f, indent=2)
   EOF
   ```

3. **Update GitHub Secret**
   - Go to Settings → Secrets
   - Update `MASTER_ENCRYPTION_KEY` with new key

4. **Commit and push**
   ```bash
   git add assets/
   git commit -m "chore: Re-encrypt assets with new master key"
   git push origin main
   ```

5. **Verify deployment**
   - Watch GitHub Actions workflow
   - Check Golem API for updated assets

6. **Revoke old key**
   - Remove from all systems
   - Document rotation in audit log

## Troubleshooting

### Decryption Fails: "GCM tag verification failed"
- **Cause**: Wrong master key or corrupted ciphertext
- **Solution**: Verify master key matches, check file integrity

### API Connection Error
- **Cause**: Endpoint URL incorrect or network unreachable
- **Solution**: Verify `GOLEM_API_EAST_*` secrets, check network connectivity

### "Missing environment variable: GOLEM_API_EAST_1"
- **Cause**: Secret not configured
- **Solution**: Add all 5 required secrets to GitHub (see Step 2)

### Workflow "Deployment error for east-1"
- **Cause**: API credentials invalid or endpoint down
- **Solution**: Verify credentials, check Golem API status, review workflow logs

## Compliance & Audit

### Audit Logging
All operations are logged in GitHub Actions:
- Timestamp (UTC)
- Operation (encrypt/decrypt/upload)
- Region (east-1/east-2)
- Asset name
- Success/failure status
- Actor (GitHub user)
- Commit SHA

### View Audit Logs
1. Go to: **Actions** → **Encrypt & Deploy Assets to Golem**
2. Click workflow run
3. Expand **Audit log** step
4. Export to CSV if needed

### Security Checklist

- [ ] Master encryption key stored in GitHub Secrets only
- [ ] Never commit unencrypted sensitive assets
- [ ] Never commit master key to repository
- [ ] API credentials in GitHub Secrets (not in code)
- [ ] TLS certificate validation enabled
- [ ] 90-day key rotation schedule established
- [ ] Audit logs reviewed regularly
- [ ] Team trained on encryption procedures
- [ ] Disaster recovery procedure documented
- [ ] Emergency key revocation plan in place

## References

- [NIST SP 800-38D - GCM Mode](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-38d.pdf)
- [RFC 2898 - PBKDF2](https://datatracker.ietf.org/doc/html/rfc2898)
- [Cryptography.io AES-GCM](https://cryptography.io/en/latest/hazmat/primitives/ciphers/)
- [Golem API Documentation](https://docs.golem.network/)

---

**Last Updated**: 2026-06-13  
**Version**: 1.0  
**Status**: Production Ready
