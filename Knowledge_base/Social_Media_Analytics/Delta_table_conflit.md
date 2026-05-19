# Delta Table Write Conflict: cannot overwrite table tweets

## Problem
Notebook execution failed with:

```text
Cannot overwrite table default.tweets_data_temp that is also being read from
```

This prevented data overwrite operations during notebook execution.

## Root Cause
The notebook attempted to overwrite a Delta table while simultaneously reading from the same table within the active Spark session.  
This created a read-write conflict in Spark.

## Solution
The Spark session and pool were restarted to release active table locks and cached operations.

## Resolution Steps

1. Restarted the Spark pool
2. Restarted the notebook session
3. Re-ran the notebook execution

This cleared the conflicting table state and allowed overwrite operations to complete successfully.

## Environment
- Azure Synapse Analytics
- Apache Spark
- Delta Tables
- Social Media Analytics Solution

## Tags
Delta Table, Spark, Synapse, Read Write Conflict, Notebook Execution

## Metadata
- Project: Social Media Analytics
- Category: Spark Data Processing
- Status: Resolved through Spark session restart