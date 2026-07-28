source "$FIXTURE_DIR/../../lib.sh"
init_repo
stage_feature
# Unstaged, and loudly named so any mention in the message is unambiguous.
mkdir -p src/payments
cat > src/payments/refund-gateway.js <<'UNSTAGED'
// UNSTAGED WORK — must not appear in the commit message.
export const REFUND_GATEWAY_TIMEOUT_MS = 30000;

export async function issueChargebackRefund(chargeId, cents) {
  return { chargeId, cents, gateway: 'stripe-chargeback-v2' };
}
UNSTAGED
