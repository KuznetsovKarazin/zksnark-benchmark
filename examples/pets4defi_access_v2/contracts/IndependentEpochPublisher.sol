// SPDX-License-Identifier: MIT
pragma solidity 0.8.37;
import "./BatchedPolicyRegistry.sol";

interface IEpochPoseidon {
    function poseidon(uint256[2] calldata pair) external view returns (uint256);
}

/// Four authenticated submissions make one atomic combined epoch. Each issuer blinds
/// its credential tree in a reserved slot. The entropy and witness service are off-chain.
contract IndependentEpochPublisher {
    uint256 private constant FIELD =
        21888242871839275222246405745257275088548364400416034343698204186575808495617;
    IEpochPoseidon public immutable hasher;
    uint64 public immutable origin;
    uint64 public immutable period;
    uint64 public immutable lag;
    uint64 public immutable ttl;
    uint256 public immutable policyRoot;
    uint256 public immutable minTier;
    mapping(address => uint8) private slotPlusOne;
    uint256[4] public lastSubmittedRoot;
    uint256[4] private leaves;
    uint64 public pendingCutoff;
    uint8 public received;
    bool private started;
    BatchedPolicyRegistry public registry;
    error InvalidConfiguration();
    error InvalidSubmission();

    constructor(address[4] memory signers, IEpochPoseidon poseidon, uint256 policy,
        uint256 tier, uint64 ttl_, uint64 origin_, uint64 period_, uint64 lag_) {
        if (address(poseidon).code.length == 0 || period_ <= lag_ || lag_ == 0 ||
            ttl_ == 0 || policy == 0 || policy >= FIELD || tier >= FIELD) revert InvalidConfiguration();
        for (uint8 i = 0; i < 4; i++) {
            if (signers[i] == address(0) || slotPlusOne[signers[i]] != 0) revert InvalidConfiguration();
            slotPlusOne[signers[i]] = i + 1;
        }
        hasher = poseidon;
        (policyRoot, minTier, ttl, origin, period, lag) = (policy, tier, ttl_, origin_, period_, lag_);
    }

    function submit(uint64 cutoff, uint256 localRoot) external {
        uint8 slot = slotPlusOne[msg.sender];
        if (slot == 0 || localRoot == 0 || localRoot >= FIELD || cutoff < origin ||
            (cutoff - origin) % period != 0 || block.timestamp < cutoff ||
            block.timestamp > uint256(cutoff) + lag) revert InvalidSubmission();
        uint8 index = slot - 1;
        uint8 bit = uint8(1 << index);
        if (!started || cutoff > pendingCutoff) {
            pendingCutoff = cutoff;
            received = 0;
            started = true;
        }
        if (cutoff != pendingCutoff || (received & bit) != 0 ||
            localRoot == lastSubmittedRoot[index]) revert InvalidSubmission();
        lastSubmittedRoot[index] = localRoot;
        leaves[index] = _hash(_hash(21, uint160(msg.sender)), localRoot);
        received |= bit;
        if (received == 15) {
            uint256 combined = _hash(_hash(leaves[0], leaves[1]), _hash(leaves[2], leaves[3]));
            if (address(registry) == address(0)) {
                registry = new BatchedPolicyRegistry(address(this), combined, policyRoot,
                    minTier, ttl, period, lag, cutoff);
            } else {
                registry.publishCombinedRoot(combined, cutoff);
            }
        }
    }
    function _hash(uint256 a, uint256 b) private view returns (uint256) {
        return hasher.poseidon([a,b]);
    }
}
