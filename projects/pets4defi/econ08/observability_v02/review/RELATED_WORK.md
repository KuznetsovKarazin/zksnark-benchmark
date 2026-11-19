# Prior art and remaining novelty gate

Checked 16 November 2026. This is a targeted comparison, not a systematic literature review. No originality claim is made from absence of a matching phrase. Page numbers below are printed section/page labels where specified.

| Source | Existing contribution relevant here | What the pilot may add, subject to review |
|---|---|---|
| R1 Ethereum Foundation, 3 Nov 2026 | Shared issuer and revocation registries, hidden issuer membership, anonymous revocation writes, root-history grace. Off-chain verification. Deployment-dependent anonymity and narrower sets under old roots are acknowledged. | Explicitly linkable on-chain cached accesses, observable refresh classes, and history-aware admission. The issuer-labeled attacker does not directly apply to anonymous writes without extra information. No EF vulnerability is demonstrated. |
| R2 ABC4Trust D2.2, section 2.8.6, printed p24 | Selective malicious revocation can narrow a user across presentations; individualized updates immediately before presentation can leak timing. Regular updates are recommended. | Passive labeled-publication/cache channel and its quantitative cost in a concrete workload. The attack principle is already known. |
| R3 Bobolz et al., CANS 2021, section 6 revocation | Issuer-hiding proofs and credential revocation with possibly one revocation authority per issuer; revocation authority key is hidden. | Operational outcome histories and cache behavior are additional assumptions, not a cryptographic break or an invention of hidden-authority revocation. |
| R4 Connolly et al., PKC 2022 | Signer-hiding credentials, user-selected anonymity sets, formal cryptographic constructions. | Separate proof privacy conditional on a valid statement from information released by changing valid-statement sets and public outcomes. Full security-model comparison remains to be completed. |
| R5 RFC 5280 and RFC 6960 | CRL/OCSP update-time semantics and status validity checks. CRL thisUpdate denotes issue time; OCSP thisUpdate denotes most recent time the status was known correct. These are not interchangeable without an ingestion-lag assumption. | Freshness is an assumption and engineering constraint here, not a new theorem. |
| R6 Rivest 1998 | Acceptor-defined recency requirements and supplying fresh evidence. | No novelty claimed for a source-age cap or for bounding acceptance by it. |
| R7 SMRP draft 00, 15 Nov 2026 | Shared signed freshness checkpoints, nonmembership proofs, conditional last-acceptance bound; Experimental Internet-Draft. | Different application and on-chain outcome observations. This pilot does not improve its freshness theorem. |
| PUB01, submitted manuscript | Revocation spillovers, cached authorizations, timing and gas cost sharing. | Issuer inference and availability-history constraints could be a distinct question if a realizable mechanism or nontrivial bound survives review. Merely relabeling spillover as privacy cost is insufficient. |

## Sources

R1. Vivian Plasencia and Vikas Rushi. Private Credential Verification with Issuer Hiding and Revocation. Ethereum Foundation, 3 November 2026. Sections What we built and Limitations.
https://publicsector.ethereum.foundation/articles/issuer-hiding-credentials/
Implementation threat model: https://github.com/ethereum/coordination-network/blob/main/specs/threat-model-phase-1.md

R2. ABC4Trust. Deliverable D2.2, Final version 1.0. Section 2.8.6 Revocation, printed p24.
https://abc4trust.eu/download/Deliverable_D2.2.pdf

R3. Jan Bobolz, Fabian Eidens, Stephan Krenn, Sebastian Ramacher, Kai Samelin. Issuer-Hiding Attribute-Based Credentials. CANS 2021, pp158-178. DOI 10.1007/978-3-030-92548-2_9. Author/project manuscript, section 6.
https://krakenh2020.eu/sites/kraken/files/public/content-files/2022/Issuer-Hiding-ABCs.pdf

R4. Aisling Connolly, Pascal Lafourcade, Octavio Perez Kempner. Improved Constructions of Anonymous Credentials from Structure-Preserving Signatures on Equivalence Classes. PKC 2022, pp409-438. Author manuscript.
https://sancy.iut.uca.fr/~lafourcade/PAPERS/PDF/pkc2022.pdf

R5. RFC 5280, sections 5.1.2.4-5.1.2.5; RFC 6960, section 2.4.
https://www.rfc-editor.org/rfc/rfc5280
https://www.rfc-editor.org/rfc/rfc6960

R6. Ronald L. Rivest. Can We Eliminate Certificate Revocation Lists? Financial Cryptography 1998. Section 2.
https://people.csail.mit.edu/rivest/pubs/Riv98b.pdf

R7. J.-J. Grund, R. Khatoun, G. Pujolle, A. Serhrouchni. Stapled Merkle Revocation Proofs for Pseudonymous ITS Credentials. draft-grund-khatoun-pujolle-serhrouchni-smrp-00, 15 November 2026. Work in progress, not an adopted standard.
https://www.ietf.org/ietf-ftp/internet-drafts/draft-grund-khatoun-pujolle-serhrouchni-smrp-00.html

## Questions for an independent reviewer

1. Is the selective-cache oracle implementable with a genuinely hidden issuer and distinguishable cheap cache hits, without assuming a trusted secret-issuer lookup or leaking the index directly?
2. Does the two-sided history partition condition add anything beyond known intersection/selective-failure results when specialized to cached issuer-hiding access? Identify the closest earlier theorem or protocol.
3. Which observer is defensible for our application: public chain only, service verifier with all attempts, or issuer colluding with an observer? Which publications can each observer label?
4. Is a cardinality guarantee meaningful here, or must the next model enforce a posterior cap under unequal priors and activities?
5. Does event-triggered full cover simply reproduce the already studied common epoch, leaving no new mechanism? What concrete mechanism or stronger boundary would justify a separate paper from PUB01?
6. Given the negative pooling result, is the standalone economic article a better allocation of effort? Version 0.2 supplies a bounded task on cost incidence and compensation; it does not reopen the completed funding-pool calculation.


## Version 0.2 additions

R8. George Danezis. Statistical Disclosure Attacks: Traffic Confirmation in Open
Environments. SEC 2003, pp421–426. The disclosure/intersection attack family is
prior art, not a new attack principle introduced by this pilot.
https://www.freehaven.net/anonbib/cache/statistical-disclosure.pdf

R9. George Danezis and Andrei Serjantov. Statistical Disclosure or Intersection
Attacks on Anonymity Systems. Information Hiding 2004, pp293–308.
https://doi.org/10.1007/978-3-540-30114-1_21
Author institutional record:
https://www.cl.cam.ac.uk/research/security/publications/

R10. Cynthia Dwork and Aaron Roth. The Algorithmic Foundations of Differential
Privacy. 2014, Definition 2.4 and the privacy-loss discussion. A finite pure
likelihood-ratio guarantee must cover every output in both directions. The
zero-probability hit counterexample excludes the proposed ln(1/rho) interpretation.
Our secret is issuer identity conditional on a fixed public trace; no database
adjacency definition is silently assumed.
https://www.cis.upenn.edu/~aaroth/Papers/privacybook.pdf

The v0.2 conditional propositions do not require implementing a private selective
cache: they quantify a lower bound inside its stipulated architecture. Whether that
specialization plus empirical costs is a sufficient publication contribution still
requires independent assessment. No attack against EF is claimed by adding an
anonymous-publication clustering experiment.

R11. Lloyd S. Shapley. A Value for n-Person Games. Contributions to the Theory
of Games II, 1953. Original cost/value-allocation reference; the allocation rule
is not a new contribution here.
https://doi.org/10.1515/9781400881970-018
