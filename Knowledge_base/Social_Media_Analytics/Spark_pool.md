# Spark Pool: Memory Exhaustion Issue

## Problem
Notebook execution failed with:

```text
InvalidHttpRequestToLivy
```

The Spark pool returned HTTP status code 400 due to executor memory exhaustion and insufficient available resources.

## Root Cause
The existing Spark pool configuration did not provide sufficient memory and executor capacity for the notebook workload.  
Additionally, regional infrastructure limitations were identified within the Western Europe region.

## Solution
The issue was resolved by creating a new Spark pool and reattaching notebooks to the new environment.

## Resolution Steps

1. Created a new Spark pool
2. Reattached all notebooks to the new Spark pool
3. Re-ran notebook execution
4. Added additional vHDs as advised by Microsoft support

The new pool configuration resolved the executor memory allocation issue.

## Environment
- Azure Synapse Analytics
- Apache Spark
- Livy
- Western Europe Azure Region

## Tags
Spark Pool, Livy, Executor Memory, Synapse, Apache Spark, Resource Allocation

## Metadata
- Project: Social Media Analytics
- Category: Spark Memory Management
- Status: Resolved through Spark pool recreation and infrastructure adjustment