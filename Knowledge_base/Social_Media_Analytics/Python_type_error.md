# Python Type Error: Notebook Execution failed

## Problem
Notebook execution failed with the following Python error:

```text
TypeError: int() argument must be a string, a bytes-like object or a number, not 'function'
```

This interrupted notebook processing during runtime.

## Root Cause
A variable name used in the notebook conflicted with a built-in Python function name.  
As a result, the `int()` function received a function reference instead of a valid numeric value.

## Solution
The issue was resolved by validating the variable assignment and correcting the conflicting variable name.

## Resolution Steps

1. Reviewed the variable definitions in the notebook
2. Confirmed the variable passed into `int()` was not overriding a built-in function
3. Renamed conflicting variables where necessary
4. Re-ran notebook execution successfully

## Environment
- Python
- Azure Synapse Notebook
- Apache Spark

## Tags
Python, TypeError, int(), Function Conflict, Notebook Execution, Synapse

## Metadata
- Project: Social Media Analytics
- Category: Python Runtime Error
- Status: Resolved through variable correction and validation