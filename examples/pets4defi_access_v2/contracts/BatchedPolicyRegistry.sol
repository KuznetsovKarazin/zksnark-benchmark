// SPDX-License-Identifier: MIT
pragma solidity 0.8.37;

/// @notice Experimental combined-root adapter for the unchanged PolicyGate and
/// four-issuer circuit. Deploy ONLY with zkMode=true, policyMode=1, delta=0,
/// rootGrace=0. Signed credentials and policyMode=0 are not supported.
/// @dev A trusted coordinator receives complete issuer roots privately and
/// computes the same Poseidon tree off chain. This contract does NOT prove
/// completeness or root correctness. Publishing issuer-specific inputs on any
/// public upstream channel defeats the intended publisher-label suppression.
contract BatchedPolicyRegistry {
    uint256 public constant FIELD =
        21888242871839275222246405745257275088548364400416034343698204186575808495617;
    address public immutable coordinator;
    uint64 public immutable period;
    uint64 public immutable origin;
    uint64 public immutable publicationLag;
    uint64 public immutable maxTTL;
    uint256 public immutable policyRoot;
    uint256 public immutable minTier;
    uint256 public constant policyVersion = 1;
    uint256 public registryRoot;
    uint256 public publicationEpoch = 1;
    uint256 public securityEpoch = 1;
    uint64 public asOf;
    uint64 public freshUntil;

    struct RootRecord { uint256 securityEpoch_; uint64 supersededAt; bool exists; }
    mapping(uint256 => RootRecord) public roots;
    event BatchPublished(uint256 root, uint64 asOf, uint64 freshUntil, uint256 epoch);
    error InvalidConfiguration();
    error Unauthorized();
    error InvalidRoot();
    error InvalidSlot();

    constructor(address coordinator_, uint256 root_, uint256 policyRoot_,
        uint256 minTier_, uint64 ttl_, uint64 period_, uint64 lag_, uint64 asOf_) {
        if (coordinator_ == address(0) || period_ == 0 || lag_ == 0 || lag_ >= period_ ||
            ttl_ == 0 || minTier_ >= FIELD || policyRoot_ == 0 || policyRoot_ >= FIELD) {
            revert InvalidConfiguration();
        }
        coordinator = coordinator_;
        period = period_;
        origin = asOf_;
        publicationLag = lag_;
        maxTTL = ttl_;
        policyRoot = policyRoot_;
        minTier = minTier_;
        _checkRoot(root_);
        _checkSlot(asOf_);
        registryRoot = root_;
        asOf = asOf_;
        freshUntil = asOf_ + period_ + lag_;
        roots[root_] = RootRecord(1, 0, true);
        emit BatchPublished(root_, asOf_, freshUntil, 1);
    }

    /// @dev An unchanged root is an intentional heartbeat. Skipped slots may be
    /// recovered with the current slot, but the gap fails closed after freshUntil.
    function publishCombinedRoot(uint256 root_, uint64 cutoff) external {
        if (msg.sender != coordinator) revert Unauthorized();
        _checkRoot(root_);
        _checkSlot(cutoff);
        if (cutoff <= asOf) revert InvalidSlot();
        roots[registryRoot].supersededAt = uint64(block.timestamp);
        ++publicationEpoch;
        ++securityEpoch;
        registryRoot = root_;
        asOf = cutoff;
        freshUntil = cutoff + period + publicationLag;
        roots[root_] = RootRecord(securityEpoch, 0, true);
        emit BatchPublished(root_, cutoff, freshUntil, securityEpoch);
    }

    function _checkSlot(uint64 cutoff) private view {
        if (cutoff < origin || (cutoff - origin) % period != 0 || cutoff > block.timestamp ||
            block.timestamp > uint256(cutoff) + publicationLag) revert InvalidSlot();
    }
    function _checkRoot(uint256 value) private pure {
        if (value == 0 || value >= FIELD) revert InvalidRoot();
    }
    function securityDeadline(uint256 epoch_, uint64 delta)
        external view returns (bool ok, uint64 deadline) {
        deadline = freshUntil;
        ok = delta == 0 && epoch_ == securityEpoch && block.timestamp < deadline;
    }
    function acceptedRoot(uint256 root_, uint64 delta, uint64 rootGrace)
        external view returns (bool ok, uint256 epoch_, uint64 deadline) {
        epoch_ = roots[root_].securityEpoch_;
        deadline = freshUntil;
        ok = delta == 0 && rootGrace == 0 && root_ == registryRoot &&
            roots[root_].exists && epoch_ == securityEpoch && block.timestamp < deadline;
    }
    // This adapter deliberately provides no public issuer list or signed mode.
    function isIssuerActive(address) external pure returns (bool) { return false; }
    function revokedAt(address, uint256) external pure returns (uint64) { return 0; }
}
