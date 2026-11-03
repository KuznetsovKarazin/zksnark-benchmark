# Pilot result — 20 October 2026

The complete local workflow passed **44 integration/cryptographic checks and
14 economic-model tests**. It executed six successful deposits per variant and
exported **270 paired economic scenarios**. The latter are event-model
projections, not 270 independently executed on-chain workloads.

Source: `005e230f496c112e3781aa79f7560e426aedbb80`. This published commit has
the exact Git tree of the executed local commit; both identifiers and the tree
are recorded in `results/measurements.json`. Measured code was clean. Every CSV
row carries the input-file hash and source provenance.

## Measured local execution

| Event | B0: signed eligibility | B1: signed commitment + ZK | Samples per variant |
| --- | ---: | ---: | ---: |
| Initial token approval | 46,463 gas | 46,463 gas | 1 |
| First holder deposit, excluding approval | 99,774 gas | 312,107 gas | 1 |
| Repeat deposit, mean | 65,586 gas | 277,940.6 gas | 5 |
| Gate deployment | 989,928 gas | 992,614 gas | 1 |
| Verifier deployment | Not needed | 385,549 gas | 1 for B1 |
| Credential revocation | 44,824 gas | 44,824 gas | 1 |

The B1 repeat range was 277,895–277,955 gas. Proof/calldata bytes can vary
between runs. Shared gate token balances were initialized before measurement;
the bootstrap transfer and token deployment are separate fixed events.

Six B1 proofs took **376.4–470.1 ms**, mean **426.7 ms**, for the `fullProve`
boundary defined in README. This includes witness generation and proving.
Off-chain verification took 15.2–344.9 ms, with the cold first invocation much
slower than later invocations. The scenario exporter pools observations for
both cohorts; these are process timings, not user-cohort effects.

Environment: AMD EPYC 9V74, x64, Node 24.19.0, Ganache 7.9.2, local Shanghai
EVM, Solidity 0.8.37 targeting Shanghai with optimizer 200. The installed
Ganache native uWS binary did not support this Node build, so Ganache used its
JavaScript fallback. No RPC/network latency is included. Exact dependencies,
machine information and setup hashes are in the measurement JSON.

## Interpretation

At an **assumed effective price of 10 gwei**, one repeat deposit's measured
gas corresponds to 0.00065586 ETH for B0 and 0.002779406 ETH for B1. The
increment is 0.002123546 ETH. These are conditional chain-fee conversions,
not current market quotations or complete KYC/service prices.

This pilot quantifies the additional cost of a particular verifiable
predicate architecture. It does not establish a privacy benefit over B0:
B0 already reveals only a signed eligibility bit, while B1 retains a public,
stable commitment and holder. Issuer prices, refresh prices, operating costs,
adoption and user willingness to pay have not been measured.

The 30/90/365-day sweep changes renewal counts. It uses gas from the measured
90-day credential fixture; it does not measure separate issuer workflows or
every alternative expiry/signature's calldata. Cost-sharing changes the payer,
not gas consumption, and is not implemented as a relayer.

## Review and remaining scope

An independent automated code/model review found and corrected shared-state
initialization being charged per new user, stale setup-artifact reuse, weak
witness-error assertions, and the binding of expiry-test fixtures. This is
not a human acceptance or a production security audit.

The test report lists the exact checks. Separate adversarial-token/reentrancy
tests, a positive `expiry−1` boundary case, cross-application credential reuse,
mainnet-fork benchmarking and a real issuer integration remain outside this
pilot. Economic conclusions must retain these boundaries.

Start the economic review with [HANDOFF.md](HANDOFF.md).
