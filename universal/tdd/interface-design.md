# Interface Design for Testability

Good interfaces make testing natural:

1. **Accept dependencies, don't create them**

   ```
   // Testable — dependency injected
   function processOrder(order, paymentGateway)

   // Hard to test — dependency created internally
   function processOrder(order):
       gateway = new StripeGateway()
   ```

2. **Return results, don't produce side effects**

   ```
   // Testable — returns a value
   function calculateDiscount(cart) -> Discount

   // Hard to test — mutates input
   function applyDiscount(cart) -> void:
       cart.total -= discount
   ```

3. **Small surface area**
   - Fewer methods = fewer tests needed
   - Fewer params = simpler test setup
