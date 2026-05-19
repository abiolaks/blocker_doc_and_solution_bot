---
name: tdd
description: Test-driven development with red-green-refactor loop for Python (pytest + mypy + ruff). Use when implementing features, fixing bugs, or when the task says "use /tdd".
---

# Test-Driven Development

## Philosophy

Tests verify **behavior through public interfaces**, not implementation details. Code can change entirely; tests shouldn't.

A good test reads like a specification — "user can withdraw funds" tells you exactly what capability exists. It survives refactors because it doesn't care about internal structure.

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
# GOOD: tests observable behavior through public API
def test_withdraw_reduces_balance(account):
    account.deposit(100)
    result = account.withdraw(30)
    assert result == 30
    assert account.balance == 70

# BAD: tests implementation details
def test_withdraw_calls_validate(mocker):
    mock_validate = mocker.patch.object(Account, "_validate")
    account = Account(balance=100)
    account.withdraw(30)
    mock_validate.assert_called_once()

# BAD: bypasses interface to verify
def test_create_user_saves_to_db(db_session):
    create_user(name="Alice")
    row = db_session.execute("SELECT * FROM users WHERE name = 'Alice'").first()
    assert row is not None

# GOOD: verifies through public interface
def test_create_user_makes_user_retrievable(db_session):
    user = create_user(name="Alice")
    retrieved = get_user(user.id)
    assert retrieved.name == "Alice"
```

## Mocking

Only mock at **system boundaries** — things you don't control:

- External APIs, databases, filesystem, network
- Time (`freezegun`), randomness
- Anything with side effects outside the process

Never mock:
- Your own classes, modules, or functions
- Internal collaborators

Prefer dependency injection so boundaries are mockable:

```python
# Easy to test: dependency injected
def send_notification(user, *, email_client):
    return email_client.send(user.email, "Hello")

# Hard to test: creates dependency internally
def send_notification(user):
    client = SmtpClient(host=config.SMTP_HOST)
    return client.send(user.email, "Hello")
```

For web frameworks (FastAPI, Flask), use the framework's test client — it exercises the full stack without mocking internals.

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
