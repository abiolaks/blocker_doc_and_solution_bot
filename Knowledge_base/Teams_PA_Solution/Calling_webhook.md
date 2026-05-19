# Calling Webhook: calling webhook was required

## Problem
The “Webhook for Calling” field was required during bot setup.

## Root Cause
Teams calling bots require a public HTTPS callback endpoint to receive meeting and call events from Microsoft.

## Solution
Built a backend API endpoint, `/api/calling`, and configured it as the Calling Webhook.

## Environment
- Azure Bot Service
- Backend API
- Microsoft Teams

## Tags
Calling Webhook, Teams Bot, API Endpoint

## Metadata
- Project: Teams PA Solution
- Category: Webhook Configuration
- Status: Resolved through backend callback endpoint setup