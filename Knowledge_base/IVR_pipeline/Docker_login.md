# Docker Login Credential Store Error

## Problem
Docker login failed with:

```text
error saving credentials: pass not initialized
```

## Root Cause
The Linux password store (`pass`) and GPG key infrastructure were not initialized.

## Solution
Installed `pass` and `gnupg`, generated a GPG key, and initialized the password store.

## Resolution Steps

1. Installed dependencies:

```bash
sudo apt-get install -y pass gnupg
```

2. Generated GPG key:

```bash
gpg --full-generate-key
```

3. Listed generated keys:

```bash
gpg --list-secret-keys --keyid-format LONG
```

4. Initialized password store:

```bash
pass init FF1263749E738518
```

5. Re-ran Docker login successfully

## Environment
- Docker
- Linux
- GPG
- pass

## Tags
Docker Login, pass, GPG, Credential Store

## Metadata
- Project: AI Infrastructure Setup
- Category: Docker Authentication
- Status: Resolved through password store initialization