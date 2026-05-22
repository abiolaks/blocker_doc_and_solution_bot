# Stale Knowledge From Missing Re-ingestion Schedule

## Problem
The agent risked answering questions using outdated document content.

## Root Cause
The source documents in Blob Storage could change, but no refresh or re-ingestion schedule was configured for Azure AI Search.

## Solution
Configured a scheduled refresh for the Azure AI Search indexer.

## Resolution Steps

1. Opened the Azure AI Search indexer
2. Went to scheduling settings
3. Configured refresh frequency, such as daily or hourly
4. Saved the schedule
5. Verified that updated source documents were re-indexed

## Environment
- Azure AI Search
- Blob Storage
- Foundry Agent

## Tags
Indexer, Re-ingestion, Scheduled Refresh, Stale Data

## Metadata
- Project: Foundry RAG AI Assistant
- Category: Data Refresh & Indexing
- Status: Resolved through scheduled re-ingestion configuration