# TECH-01 / ECON-03: handoff to Nataliya

The v2 code and evidence replace the original 270-row v1 projection as the working TECH-01 input. Keep v1 for the history; do not combine its gas numbers with the new architecture.

ECON-01 remains accepted as the preliminary research audit and problem statement. ECON-02 remains a separate Louafi reproducibility exercise. The new experiment is not a claimed reproduction of Louafi's model.

Please use the existing TECH-01 and ECON-03 cards; no new cards are needed for individual parameter values or each treatment.

## A manageable first deliverable

Please read README.md, THREAT_MODEL.md and ECONOMICS.md, then prepare a short note with:

1. **One comparison table:** signed direct / signed cached / ZK direct / ZK cached, using RESULTS.md and the underlying CSVs. Separate one-time costs, recurring access, reauthorization and costs still unknown.
2. **One worked workload:** 100 total accesses across one or five services, 1,000 users, 90-day horizon, 30-day authorization TTL. Compare no background root changes with daily changes; then check 30- versus 90-day credential validity. Explain the cache-hit counts from the trace before interpreting costs.
3. **A short conclusion and input request:** when caching saves gas, when root changes erase that benefit, and which missing prices/data could change the economic conclusion. Do not assign arbitrary issuer, GDPR, witness-service or mobile-user costs.

The full 96-context export is available for checking sensitivity; the first written note does not need to discuss every row. Alpha values 0%, 25%, 50%, 75%, 100% are payment allocation examples and do not change total resource cost.

## Responsibilities and review status

- Alexander: confirm the scientific comparison and synthetic policy, review the interpretation, and arrange the remaining technical/device measurements.
- Nataliya: inspect the accounting assumptions, produce the concise economic comparison and identify missing empirical inputs.
- Riccardo: keep links/version decisions together on the existing cards and record the accepted scope; no cryptographic implementation work is requested from him.

TECH-01 is a reviewed prototype handoff, not a production certification. Browser/phone timing, complete L2 fees, issuer/witness service and independent phase-2 ceremony remain separate stated gaps. ECON-03 can begin its conditional analysis while those unknowns remain clearly labelled.
