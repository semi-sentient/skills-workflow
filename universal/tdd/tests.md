# Good and Bad Tests

Examples use pseudocode — adapt to your project's language and test framework.

## Good Tests

**Integration-style**: Test through real interfaces, not mocks of internal parts.

```
// GOOD: Tests observable behavior
test "user can checkout with valid cart":
    cart = createCart()
    cart.add(product)
    result = checkout(cart, paymentMethod)
    assert result.status == "confirmed"
```

Characteristics:

- Tests behavior users/callers care about
- Uses public API only
- Survives internal refactors
- Describes WHAT, not HOW
- One logical assertion per test

## Bad Tests

**Implementation-detail tests**: Coupled to internal structure.

```
// BAD: Tests implementation details
test "checkout calls paymentService.process":
    mockPayment = mock(paymentService)
    checkout(cart, payment)
    assert mockPayment.process was called with cart.total
```

Red flags:

- Mocking internal collaborators
- Testing private methods
- Asserting on call counts/order
- Test breaks when refactoring without behavior change
- Test name describes HOW not WHAT
- Verifying through external means instead of interface

```
// BAD: Bypasses interface to verify
test "createUser saves to database":
    createUser({ name: "Alice" })
    row = db.query("SELECT * FROM users WHERE name = ?", ["Alice"])
    assert row is defined

// GOOD: Verifies through interface
test "createUser makes user retrievable":
    user = createUser({ name: "Alice" })
    retrieved = getUser(user.id)
    assert retrieved.name == "Alice"
```
