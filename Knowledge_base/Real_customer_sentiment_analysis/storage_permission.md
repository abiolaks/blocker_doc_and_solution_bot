# Storage Permission Issue:Blob storage wasn't accessed

## Problem
The Azure Function application failed to access Blob Storage resources during runtime execution.

## Root Cause
The Function App lacked valid authentication credentials or sufficient permissions to access the storage account.  
The configured storage connection string or managed identity role assignment was incomplete or incorrect.

## Solution
The storage authentication configuration was corrected.

## Resolution Steps

1. Validated the BLOB_CONNECTION_STRING value
2. Updated the connection string where necessary
3. Alternatively assigned the required RBAC role to the Function App managed identity
4. Restarted the Function App
5. Re-tested storage access operations

After permissions were corrected, the Function App accessed Blob Storage successfully.

## Environment
- Azure Functions
- Azure Blob Storage
- Managed Identity
- Azure RBAC

## Tags
Azure Storage, Managed Identity, RBAC, Blob Access, Azure Functions

## Metadata
- Project: Real-Time Customer Sentiment Analysis
- Category: Authentication & Permissions
- Status: Resolved through storage authentication correction