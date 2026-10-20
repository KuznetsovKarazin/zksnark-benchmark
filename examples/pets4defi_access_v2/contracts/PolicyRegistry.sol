// SPDX-License-Identifier: MIT
pragma solidity 0.8.37;

interface IPolicyPoseidon2 {
    function poseidon(uint256[2] calldata inputs) external view returns (uint256);
}

/// @notice Synthetic registry with distinct publication and revocation contexts.
/// @dev Issuers are trusted to classify additions honestly. An opaque root does
/// not prove append-only behavior. No credential issuance or witness service is
/// implemented here. Root publication may incorporate a batch for ONE issuer.
contract PolicyRegistry {
    uint256 public constant SNARK_FIELD =
        21888242871839275222246405745257275088548364400416034343698204186575808495617;
    uint64 public constant MAX_DELAY = 1 days;
    address public immutable owner;
    IPolicyPoseidon2 public immutable hasher;
    address[4] public issuers;
    uint256[4] public issuerRoots;
    bool[4] public disabled;
    mapping(address => uint256) public issuerIndexPlusOne;
    mapping(address => mapping(uint256 => uint64)) public revokedAt;

    struct RootRecord {
        uint256 securityEpoch;
        uint64 supersededAt;
        bool exists;
    }
    mapping(uint256 => RootRecord) public roots;
    mapping(uint256 => uint64) public securityInvalidatedAt;
    uint256 public registryRoot;
    uint256 public policyRoot;
    uint256 public minTier;
    uint64 public maxTTL;
    uint256 public policyVersion = 1;
    uint256 public publicationEpoch = 1;
    uint256 public securityEpoch = 1;
    uint256 public emergencyEpoch = 1;

    error ZeroAddress();
    error MissingContract();
    error DuplicateIssuer();
    error InvalidIndex();
    error NotOwner();
    error NotIssuer();
    error InactiveIssuer();
    error InvalidField();
    error InvalidPolicy();
    error InvalidDelay();
    error Unchanged();

    event IssuerRootPublished(uint256 indexed index, uint256 root, bool securityChange,
        uint256 publicationEpoch, uint256 securityEpoch);
    event PublicCredentialRevoked(address indexed issuer, uint256 indexed id, uint64 revokedTimestamp);
    event IssuerDisabled(uint256 indexed index, uint256 securityEpoch);
    event PolicyChanged(uint256 root, uint256 minTier, uint64 maxTTL, uint256 version);

    constructor(address owner_, address hasher_, address[4] memory issuers_,
        uint256 policyRoot_, uint256 minTier_, uint64 maxTTL_)
    {
        if (owner_ == address(0) || hasher_ == address(0)) revert ZeroAddress();
        if (hasher_.code.length == 0) revert MissingContract();
        _checkPolicy(policyRoot_, minTier_, maxTTL_);
        owner = owner_;
        hasher = IPolicyPoseidon2(hasher_);
        policyRoot = policyRoot_;
        minTier = minTier_;
        maxTTL = maxTTL_;
        for (uint256 i; i < 4; ++i) {
            address issuer = issuers_[i];
            if (issuer == address(0)) revert ZeroAddress();
            if (issuerIndexPlusOne[issuer] != 0) revert DuplicateIssuer();
            issuers[i] = issuer;
            issuerIndexPlusOne[issuer] = i + 1;
        }
        _rebuild();
        roots[registryRoot] = RootRecord(securityEpoch, 0, true);
    }

    function isIssuerActive(address issuer) public view returns (bool) {
        uint256 slot = issuerIndexPlusOne[issuer];
        return slot != 0 && !disabled[slot - 1] && issuerRoots[slot - 1] != 0;
    }

    function issuerLeaf(uint256 index) public view returns (uint256) {
        if (index >= 4) revert InvalidIndex();
        if (disabled[index] || issuerRoots[index] == 0) return 0;
        return _hash(_hash(21, uint256(uint160(issuers[index]))), issuerRoots[index]);
    }

    /// @dev securityChange=false is a TRUSTED issuer declaration, not an
    /// enforced append-only proof. Any removal must set it true. One root may
    /// contain any number of off-chain changes within the issuer's tree.
    function publishIssuerRoot(uint256 index, uint256 root, bool securityChange) external {
        _checkRootUpdate(index, root);
        _replaceRoot(index, root, securityChange);
    }

    /// @notice Atomically update the public signed-ID and hidden-root forms.
    /// @dev The trusted issuer must remove the corresponding hidden leaf.
    function revokeAndPublish(uint256 index, uint256 id, uint256 root) external {
        _checkRootUpdate(index, root);
        _revokePublic(id);
        _replaceRoot(index, root, true);
    }

    /// @notice Revoke the signed-ID representation only.
    /// @dev Does not claim to revoke an undisclosed leaf. Use revokeAndPublish
    /// when both representations correspond to the same real credential.
    function revokePublic(uint256 id) external {
        if (!isIssuerActive(msg.sender)) revert InactiveIssuer();
        _revokePublic(id);
        ++publicationEpoch;
    }

    function disableIssuer(uint256 index) external {
        if (msg.sender != owner) revert NotOwner();
        if (index >= 4) revert InvalidIndex();
        if (disabled[index]) revert Unchanged();
        _supersedeCurrent();
        disabled[index] = true;
        issuerRoots[index] = 0;
        _advanceSecurity(true);
        _rebuild();
        _recordCurrent();
        ++publicationEpoch;
        emit IssuerDisabled(index, securityEpoch);
    }

    /// @notice Policy changes are emergency invalidations with no grace.
    function updatePolicy(uint256 root, uint256 tier, uint64 ttl) external {
        if (msg.sender != owner) revert NotOwner();
        _checkPolicy(root, tier, ttl);
        if (root == policyRoot && tier == minTier && ttl == maxTTL) revert Unchanged();
        policyRoot = root;
        minTier = tier;
        maxTTL = ttl;
        ++policyVersion;
        _advanceSecurity(true);
        // Membership hash may be unchanged; the new context changes the action
        // binding, and old cached epochs are below the emergency floor.
        _recordCurrent();
        ++publicationEpoch;
        emit PolicyChanged(root, tier, ttl, policyVersion);
    }

    /// @return ok Whether the security context is accepted at this block.
    /// @return deadline Exclusive acceptance deadline, or uint64.max if current.
    function securityDeadline(uint256 epoch_, uint64 delta) public view returns (bool ok, uint64 deadline) {
        if (delta > MAX_DELAY) revert InvalidDelay();
        if (epoch_ == 0 || epoch_ > securityEpoch || epoch_ < emergencyEpoch) return (false, 0);
        if (epoch_ == securityEpoch) return (true, type(uint64).max);
        uint64 invalidatedTimestamp = securityInvalidatedAt[epoch_];
        if (invalidatedTimestamp == 0) return (false, 0);
        deadline = invalidatedTimestamp + delta;
        return (block.timestamp < deadline, deadline);
    }

    /// @notice Root grace bounds proof presentation, not a cache's lifetime.
    /// Security deadlines separately bound both presentation and cache use.
    function acceptedRoot(uint256 root, uint64 delta, uint64 rootGrace)
        external view returns (bool ok, uint256 epoch_, uint64 deadline)
    {
        if (rootGrace > MAX_DELAY) revert InvalidDelay();
        RootRecord memory record = roots[root];
        if (!record.exists) return (false, 0, 0);
        epoch_ = record.securityEpoch;
        (ok, deadline) = securityDeadline(epoch_, delta);
        if (!ok) return (false, epoch_, deadline);
        if (root != registryRoot) {
            uint64 rootDeadline = record.supersededAt + rootGrace;
            if (record.supersededAt == 0 || block.timestamp >= rootDeadline) return (false, epoch_, rootDeadline);
            if (rootDeadline < deadline) deadline = rootDeadline;
        }
    }

    function _checkRootUpdate(uint256 index, uint256 root) private view {
        if (index >= 4) revert InvalidIndex();
        if (msg.sender != issuers[index]) revert NotIssuer();
        if (disabled[index]) revert InactiveIssuer();
        if (root == 0 || root >= SNARK_FIELD) revert InvalidField();
        if (root == issuerRoots[index]) revert Unchanged();
    }

    function _replaceRoot(uint256 index, uint256 root, bool securityChange) private {
        _supersedeCurrent();
        issuerRoots[index] = root;
        if (securityChange) _advanceSecurity(false);
        _rebuild();
        _recordCurrent();
        ++publicationEpoch;
        emit IssuerRootPublished(index, root, securityChange, publicationEpoch, securityEpoch);
    }

    function _revokePublic(uint256 id) private {
        if (revokedAt[msg.sender][id] != 0) revert Unchanged();
        revokedAt[msg.sender][id] = uint64(block.timestamp);
        emit PublicCredentialRevoked(msg.sender, id, uint64(block.timestamp));
    }

    function _supersedeCurrent() private {
        roots[registryRoot].supersededAt = uint64(block.timestamp);
    }

    function _advanceSecurity(bool emergency) private {
        // Each epoch is invalidated once. Subsequent updates cannot move this
        // epoch's deadline or extend a revoked credential's exposure window.
        securityInvalidatedAt[securityEpoch] = uint64(block.timestamp);
        ++securityEpoch;
        if (emergency) emergencyEpoch = securityEpoch;
    }

    function _recordCurrent() private {
        roots[registryRoot] = RootRecord(securityEpoch, 0, true);
    }

    function _checkPolicy(uint256 root, uint256 tier, uint64 ttl) private pure {
        if (root == 0 || root >= SNARK_FIELD || tier > 255 || ttl == 0) revert InvalidPolicy();
    }

    function _hash(uint256 left, uint256 right) private view returns (uint256) {
        return hasher.poseidon([left, right]);
    }

    function _rebuild() private {
        registryRoot = _hash(_hash(issuerLeaf(0), issuerLeaf(1)), _hash(issuerLeaf(2), issuerLeaf(3)));
    }
}
