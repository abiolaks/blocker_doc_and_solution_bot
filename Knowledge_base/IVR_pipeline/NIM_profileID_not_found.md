# NIMProfileIDNotFound Error

## Problem
Container startup failed with:

```text
NIMProfileIDNotFound — no matching profile
```

## Root Cause
The configured `NIM_TAGS_SELECTOR` did not match any pre-built profile compatible with the RTX 5070 Ti GPU architecture.

## Solution
Removed the custom `NIM_TAGS_SELECTOR` configuration and allowed automatic profile selection.

## Resolution Steps

1. Removed:

```bash
NIM_TAGS_SELECTOR='mode=str,vad=silero,diarizer=disabled'
```

2. Started the container using default configuration
3. Allowed NIM to auto-select compatible profile settings

## Environment
- NVIDIA NIM
- RTX 5070 Ti
- Docker

## Tags
NIM, GPU Profile, RTX 5070 Ti, Container Runtime

## Metadata
- Project: AI Infrastructure Setup
- Category: NVIDIA NIM Configuration
- Status: Resolved through automatic profile selection