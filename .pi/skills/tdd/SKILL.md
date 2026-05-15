---
name: tdd
description: Test-driven development with red-green-refactor loop for Python (pytest + mypy + ruff). Use when implementing features, fixing bugs, or when the task says "use /tdd".
---

# Test-Driven Development

## Philosophy

Tests verify **behavior through public interfaces**, not implementation details. Code can change entirely; tests shouldn't.

A good test reads like a specification — "search returns matching knowledge base entries" tells you exactly what capability exists. It survives refactors because it doesn't care about internal structure.

A bad test is coupled to implementation — it mocks internal collaborators, tests private functions, or verifies by querying the database directly instead of using the interface. If you rename an internal function and tests fail, those tests were testing implementation, not behavior.

## Anti-Pattern: Horizontal Slices

**Never write all tests first, then all implementation.** This produces tests that verify imagined behavior rather than actual behavior — they end up testing the shape of data structures, not what the system does.

```
WRONG (horizontal):
  RED:   test1, test2, test3, test4, test5
  GREEN: impl1, impl2, impl3, impl4, impl5

RIGHT (vertical):
  RED→GREEN: test1→impl1
  RED→GREEN: test2→impl2
  RED→GREEN: test3→impl3
```

One test → one implementation → repeat. Each test responds to what you learned from the previous cycle.

## Good vs Bad Tests

```python
# GOOD: tests observable behavior through public interface
def test_search_returns_matching_entries(client):
    response = client.post("/search", json={"query": "FAISS index error"})
    assert response.status_code == 200
    assert len(response.json()["results"]) > 0
    assert response.json()["results"][0]["title"] is not None

# BAD: tests implementation details
def test_search_calls_faiss_index(mocker):
    mock_search = mocker.patch("app.search.faiss_index.search")
    search("FAISS index error")
    mock_search.assert_called_once()

# BAD: bypasses interface to verify
def test_save_blocker_writes_to_blob(mocker):
    mock_blob = mocker.patch("azure.storage.blob.BlobClient.upload_blob")
    save_blocker(blocker_data)
    mock_blob.assert_called_once()

# GOOD: verifies through interface
def test_save_blocker_makes_entry_retrievable(client):
    response = client.post("/blockers", json={"error": "...", "solution": "..."})
    blocker_id = response.json()["id"]
    get_resp = client.get(f"/blockers/{blocker_id}")
    assert get_resp.status_code == 200
```

## Mocking

Only mock at **system boundaries** — things you don't control:

```python
# Mock these (system boundaries)
# - External APIs: GitHub, Azure Blob/Table Storage, Teams Bot Service
# - Time: freeze_time / freezegun
# - Random: seed or mock

# Never mock these (your own code)
# - Your own classes, modules, or functions
# - Internal collaborators
```

Prefer dependency injection so boundaries are mockable:

```python
# Easy to test: dependency injected
def commit_to_kb(entry, *, github_client):
    return github_client.create_file(entry)

# Hard to test: creates dependency internally
def commit_to_kb(entry):
    client = Github(env["GITHUB_TOKEN"])
    return client.create_file(entry)
```

For FastAPI endpoints, use `TestClient` — it exercises the full stack without mocking internals.

## Workflow

### Red: Write a Failing Test

- One test, one behavior. The smallest test that captures what the system should do.
- Run `pytest path/to/test.py -v` — confirm it **fails** for the right reason.
- If it passes before you wrote code, the test is wrong.

### Green: Minimal Implementation

- Write only enough code to make this one test pass.
- No abstractions for future tests, no error handling beyond what's tested.
- Run `pytest -v` — all tests must pass.

### Refactor

Only after green:

- Extract duplication, improve names
- Run `pytest -v` after each change — stay green
- Run `mypy .` and `ruff check .`
- Don't refactor for its own sake; clean real mess, don't gold-plate

**Never refactor while red.** Get to green first.

### Repeat

Next behavior → back to Red. One vertical slice at a time.

## Checklist Per Cycle

```
[ ] Test describes behavior, not implementation
[ ] Test uses public interface only
[ ] Test would survive internal refactor
[ ] Code is minimal for this test
[ ] No speculative features added
```

## Feedback Loops

Before the task is done, all three must pass clean:

```bash
pytest -v
mypy .
ruff check .
```

## Commit

When all tests and checks pass:

1. `git status` and `git diff --stat`
2. Stage only your files: `git add <specific-files>`
3. Commit with: what was done, key decisions, files changed
4. Do NOT commit unless the user asks — stop and report completion
