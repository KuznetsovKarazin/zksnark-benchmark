// SPDX-License-Identifier: MIT
pragma solidity 0.8.37;

interface IPoseidon2 {
    function poseidon(uint256[2] calldata inputs) external view returns (uint256);
}

/// @notice Synthetic hierarchical registry: four issuer slots, depth two.
/// @dev Issuers authenticate updates to their own credential trees. This does
///      not validate real-world KYC or prove that an issuer performs it honestly.
contract AccessRegistry {
    uint256 public constant SNARK_FIELD =
        21888242871839275222246405745257275088548364400416034343698204186575808495617;
    address public immutable owner;
    IPoseidon2 public immutable hasher;
    address[4] public issuers;
    uint256[4] public issuerRoots;
    bool[4] public disabled;
    mapping(address => uint256) public issuerIndexPlusOne;
    mapping(address => mapping(uint256 => bool)) public revoked;

    uint256 public registryRoot;
    uint256 public policyRoot;
    uint256 public minTier;
    uint64 public maxTTL;
    uint256 public policyVersion = 1;
    uint256 public epoch = 1;

    error ZeroAddress();
    error MissingContract();
    error DuplicateIssuer();
    error InvalidIndex();
    error NotOwner();
    error NotIssuer();
    error InactiveIssuer();
    error InvalidField();
    error InvalidPolicy();
    error Unchanged();

    event IssuerRootChanged(uint256 indexed index, uint256 root, uint256 epoch);
    event IssuerDisabled(uint256 indexed index, uint256 epoch);
    event PolicyChanged(uint256 root, uint256 minTier, uint64 maxTTL, uint256 version, uint256 epoch);
    event PublicCredentialRevoked(address indexed issuer, uint256 indexed id, uint256 epoch);

    constructor(
        address owner_, address hasher_, address[4] memory issuers_,
        uint256 policyRoot_, uint256 minTier_, uint64 maxTTL_
    ) {
        if (owner_ == address(0) || hasher_ == address(0)) revert ZeroAddress();
        if (hasher_.code.length == 0) revert MissingContract();
        _checkPolicy(policyRoot_, minTier_, maxTTL_);
        owner = owner_;
        hasher = IPoseidon2(hasher_);
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

    function setIssuerRoot(uint256 index, uint256 root) external {
        if (index >= 4) revert InvalidIndex();
        if (msg.sender != issuers[index]) revert NotIssuer();
        if (disabled[index]) revert InactiveIssuer();
        if (root >= SNARK_FIELD) revert InvalidField();
        if (root == issuerRoots[index]) revert Unchanged();
        issuerRoots[index] = root;
        _rebuild();
        ++epoch;
        emit IssuerRootChanged(index, root, epoch);
    }

    /// @dev Permanent removal in this bounded pilot. Cannot be undone by issuer.
    function disableIssuer(uint256 index) external {
        if (msg.sender != owner) revert NotOwner();
        if (index >= 4) revert InvalidIndex();
        if (disabled[index]) revert Unchanged();
        disabled[index] = true;
        issuerRoots[index] = 0;
        _rebuild();
        ++epoch;
        emit IssuerDisabled(index, epoch);
    }

    function updatePolicy(uint256 root, uint256 tier, uint64 ttl) external {
        if (msg.sender != owner) revert NotOwner();
        _checkPolicy(root, tier, ttl);
        if (root == policyRoot && tier == minTier && ttl == maxTTL) revert Unchanged();
        policyRoot = root;
        minTier = tier;
        maxTTL = ttl;
        ++policyVersion;
        ++epoch;
        emit PolicyChanged(root, tier, ttl, policyVersion, epoch);
    }

    /// @dev Public signed IDs and hidden membership credentials are separate
    ///      revocation representations. Removing a hidden credential requires
    ///      an authenticated issuer-root update as well. Both invalidate caches.
    function revokePublic(uint256 id) external {
        if (!isIssuerActive(msg.sender)) revert InactiveIssuer();
        if (revoked[msg.sender][id]) revert Unchanged();
        revoked[msg.sender][id] = true;
        ++epoch;
        emit PublicCredentialRevoked(msg.sender, id, epoch);
    }

    function _checkPolicy(uint256 root, uint256 tier, uint64 ttl) private pure {
        if (root >= SNARK_FIELD) revert InvalidField();
        if (root == 0 || tier > 255 || ttl == 0) revert InvalidPolicy();
    }

    function _hash(uint256 left, uint256 right) private view returns (uint256) {
        return hasher.poseidon([left, right]);
    }

    function _rebuild() private {
        registryRoot = _hash(_hash(issuerLeaf(0), issuerLeaf(1)), _hash(issuerLeaf(2), issuerLeaf(3)));
    }
}
