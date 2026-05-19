# Spark Pool VCores Exhaustion Issue

## Problem
The notebook execution failed with:

```text
AVAILABLE_COMPUTE_CAPACITY_EXCEEDED
```

The live session could not start because the requested Spark resources exceeded the available vCore capacity in the Synapse workspace.

## Root Cause
The Spark pool configuration requested more compute resources than the allocated workspace capacity allowed.  
The environment attempted to use:
- 24 cores
- 48 vCores

which exceeded the available compute quota.

## Solution
The Spark pool configuration was optimized and scaled appropriately.

## Resolution Steps

1. Increased Spark node size to 16 vCores
2. Increased node count to 3–5 nodes
3. Increased default executors to 1–4
4. Submitted a Microsoft support request for vCore quota increase

This allowed notebook sessions to initialize successfully within supported compute capacity.

## Environment
- Azure Synapse Analytics
- Apache Spark Pool
- Social Media Analytics Solution

## Tags
Spark Pool, vCores, Synapse, Capacity, Compute Resources, Apache Spark

## Metadata
- Project: Social Media Analytics
- Category: Spark Infrastructure Scaling
- Status: Resolved through Spark pool optimization and capacity scaling