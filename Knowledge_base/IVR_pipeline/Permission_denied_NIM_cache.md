# Permission Denied on NIM Cache Directory

## Problem
The container failed with:

```text
Permission denied (os error 13)
```

while accessing the NIM cache directory.

## Root Cause
The cache directory was owned by the root user from a previous Docker execution.

## Solution
Corrected directory ownership and permissions.

## Resolution Steps

1. Changed ownership:

```bash
sudo chown -R aiservice:aiservice ~/.cache/nim
```

2. Updated permissions:

```bash
chmod -R 777 ~/.cache/nim
```

3. Restarted the container successfully

## Environment
- Linux
- Docker
- NVIDIA NIM

## Tags
Permission Denied, Cache Directory, Linux Permissions, NIM

## Metadata
- Project: AI Infrastructure Setup
- Category: File System Permissions
- Status: Resolved through ownership correction