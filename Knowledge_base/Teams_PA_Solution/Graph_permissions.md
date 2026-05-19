# Required Graph Permissions Unclear: Unknown required graph permission

## Problem
Uncertainty about which Microsoft Graph permissions were required.

## Root Cause
Teams meeting participation requires specialized Cloud Communications permissions.

## Solution
Added permissions such as:
- Calls.JoinGroupCall.All
- Calls.AccessMedia.All
- OnlineMeetings.Read.All

## Environment
- Microsoft Graph
- Cloud Communications API

## Tags
Graph Permissions, Teams Meetings, Cloud Communications

## Metadata
- Project: Teams PA Solution
- Category: Graph API Configuration
- Status: Resolved through required permissions setup