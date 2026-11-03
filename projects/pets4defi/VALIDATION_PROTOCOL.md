# Bounded validation of revocation timing

Prepared before the first validation run on 3 November 2026. This extends the
article's analysis; it does not reopen accepted economic stages or replace
historical input files. No contract or circuit changes are part of this test.

1. E1: four 90-day traces (two other-credential revocations at 30/60, 15/45,
   31/63, or twelve at 7,14,...,84), 100 deposits at day 0,0.9,...,89.1,
   signed and ZK caches, 30-day rolling TTL, zero allowed revocation delay.
   Expected full counts: signed 3 in every trace; ZK 3,4,5,13. Record actual
   contract choice, receipt gas, cache deadline/epoch, balances and nonce.
   Every event classification and state transition must match. Gas values
   need not match archived means exactly; quantify and explain differences.
2. Diagnostic: existing signed global-publication mode at 30/60 and weekly.
   Only revocations occur after setup, so it imposes shared invalidation.
   Expected counts 3 and 13. This isolates the importance of invalidation
   policy for authorization counts, not every component of gas expenditure.
3. E2: five distinct synthetic holder/credential seeds; first authorization,
   one cache hit, and reauthorization at exact TTL for each family. Report
   measured operation gas and the implied n=100 sign near k=4/5. Five is a
   finite state diagnostic, not a confidence-interval design.
4. Negative controls: replay of a used proof nonce; both expired caches at
   exact TTL followed by successful fresh authorization; paired atomic own
   credential revocation followed by rejection of both caches, signed full
   authorization, and a pre-update ZK proof. Included failures must leave
   token balances, deposits, contract nonce and cache unchanged.

Twenty synthetic credentials are populated, rather than the original eight,
so twelve distinct unrelated hidden leaves and their matching public IDs can
be revoked. The holder remains eligible in E1/E2. Root-update correctness is
checked against the fixture. Update honesty remains an architectural assumption.

The Hardhat timestamp option permits separate blocks at identical timestamps;
updates are ordered before access. The opcode runtime stays Osaka, compiler
target Cancun, Solidity 0.8.37, optimizer 200 and the exact committed lockfile.
Setup is fresh, hash-pinned phase 1 and local demonstration phase 2. Proof
timings collected here are diagnostics; device performance is not inferred.

Run from `examples/pets4defi_access_v2`:

```sh
npm ci
npm run setup
node scripts/revocation_validation.mjs
```

New results live in `results/revocation_validation/`. All older result files
are retained. Original economic source archives are not stored or modified
by this script. An independent colleague run remains a distinct activity.
