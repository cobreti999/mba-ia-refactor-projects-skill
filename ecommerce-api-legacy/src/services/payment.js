// Deterministic demo adapter. No network calls or real financial operations.
const APPROVED_DEMO_PREFIX = '4';
const demoPaymentGateway = Object.freeze({
    approve: card => card.startsWith(APPROVED_DEMO_PREFIX),
});

module.exports = { demoPaymentGateway };
