# Knowledge Base Not Grounding the Agent

## Problem
The Foundry agent could not answer using enterprise documents and behaved like a general-purpose model.

## Root Cause
The agent had not yet been connected to the indexed knowledge source in Azure AI Search through the Foundry knowledge connection.

## Solution
Connected the Foundry agent to the enterprise knowledge base.

## Resolution Steps

1. Opened the agent configuration in Foundry
2. Selected Add Knowledge Base
3. Connected to Foundry IQ
4. Selected the Azure AI Search resource
5. Selected the target Blob Storage-backed knowledge base
6. Configured authentication
7. Saved the knowledge connection
8. Tested the agent using questions from uploaded enterprise documents

## Environment
- Microsoft Foundry
- Foundry Agent Service
- Azure AI Search
- Azure Blob Storage

## Tags
Knowledge Base, Grounding, Foundry IQ, RAG, Azure AI Search

## Metadata
- Project: Foundry RAG AI Assistant
- Category: Agent Grounding
- Status: Resolved through knowledge base connection