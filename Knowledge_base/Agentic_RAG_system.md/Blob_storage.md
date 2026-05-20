# Foundry RAG Solution – Blob Storage Access Issue

## Problem
Azure AI Search could not reliably ingest source documents from Blob Storage.

## Root Cause
The search service or Foundry project identity did not have the required access to the Blob Storage container where enterprise documents were uploaded.

## Solution
Configured Blob Storage access permissions for the required Azure identity.

## Resolution Steps

1. Opened the Azure Storage Account
2. Verified the target Blob container
3. Confirmed the source documents were uploaded
4. Assigned the required role, such as:
   - Storage Blob Data Reader
5. Assigned the role to the Azure AI Search identity or relevant Managed Identity
6. Re-ran ingestion/indexing

## Environment
- Azure Blob Storage
- Azure AI Search
- Managed Identity
- Azure RBAC

## Tags
Blob Storage, Storage Blob Data Reader, Ingestion, Azure AI Search

## Metadata
- Project: Foundry RAG AI Assistant
- Category: Blob Storage Access
- Status: Resolved through storage role assignment