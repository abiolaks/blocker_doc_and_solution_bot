# Localhost Webhook Issue

## Problem
Localhost endpoint could not be used as the calling webhook.

## Root Cause
Microsoft cannot reach local machine URLs directly.

## Solution
Exposed the local backend using ngrok to generate a public HTTPS URL.

## Environment
- Localhost
- ngrok
- Azure Bot Service

## Tags
ngrok, Localhost, Webhook, HTTPS Endpoint

## Metadata
- Project: Teams PA Solution
- Category: Local Development Setup
- Status: Resolved through public HTTPS tunneling