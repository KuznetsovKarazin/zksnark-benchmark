// SPDX-License-Identifier: MIT
pragma solidity 0.8.37;

interface IPolicyRegistry {
    function registryRoot() external view returns (uint256);
    function policyRoot() external view returns (uint256);
    function minTier() external view returns (uint256);
    function maxTTL() external view returns (uint64);
    function policyVersion() external view returns (uint256);
    function publicationEpoch() external view returns (uint256);
    function securityEpoch() external view returns (uint256);
    function roots(uint256 root) external view returns (uint256 securityEpoch_, uint64 supersededAt, bool exists);
    function isIssuerActive(address issuer) external view returns (bool);
    function revokedAt(address issuer, uint256 id) external view returns (uint64);
    function securityDeadline(uint256 epoch_, uint64 delta) external view returns (bool ok, uint64 deadline);
    function acceptedRoot(uint256 root, uint64 delta, uint64 rootGrace)
        external view returns (bool ok, uint256 epoch_, uint64 deadline);
}

interface IPolicyDepositToken {
    function transferFrom(address sender, address recipient, uint256 amount) external returns (bool);
}

interface IPolicyVerifier {
    function verifyProof(uint256[2] calldata a, uint256[2][2] calldata b,
        uint256[2] calldata c, uint256[8] calldata publicSignals) external view returns (bool);
}

/// @notice Eligibility gates with explicitly selected status-freshness policies.
/// @dev Mode 0: any registry publication invalidates caches and queued ZK proofs.
/// Mode 1: signed credentials use individual status; ZK uses security epochs.
/// Mode 2: the same selective policies, with a bounded ordinary-revocation delay.
/// Policy changes and issuer disablement remain immediate. No legal meaning is
/// assigned to a delay. Issuer honesty about root-update classification is trusted.
contract PolicyGate {
    uint256 public constant SNARK_FIELD =
        21888242871839275222246405745257275088548364400416034343698204186575808495617;
    uint256 public constant REQUEST_MASK = (uint256(1) << 248) - 1;
    uint256 public constant POLICY_ID = 1;
    uint256 private constant HALF_ORDER =
        0x7fffffffffffffffffffffffffffffff5d576e7357a4501ddfe92f46681b20a0;
    bytes32 private constant DOMAIN_TYPEHASH = keccak256(
        "EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)");
    bytes32 public constant CREDENTIAL_TYPEHASH = keccak256(
        "Credential(address holder,uint256 id,uint256 policyVersion,uint64 validFrom,uint64 validUntil,bool eligible)");

    struct Credential {
        address holder;
        uint256 id;
        uint256 policyVersion;
        uint64 validFrom;
        uint64 validUntil;
        bool eligible;
    }
    struct Proof {
        uint256[2] a;
        uint256[2][2] b;
        uint256[2] c;
        // [N, registryRoot, policyRoot, minTier, start, end, scope, requestHash]
        uint256[8] publicSignals;
    }
    struct Authorization {
        uint64 until;
        uint256 publicationEpoch;
        uint256 securityEpoch;
        uint256 nullifier;
        address issuer;
        uint256 credentialId;
        uint256 policyVersion;
    }

    IPolicyRegistry public immutable registry;
    IPolicyDepositToken public immutable token;
    IPolicyVerifier public immutable verifier;
    bool public immutable zkMode;
    bool public immutable cacheEnabled;
    uint8 public immutable policyMode;
    uint64 public immutable deltaSeconds;
    uint64 public immutable rootGraceSeconds;
    mapping(address => Authorization) public caches;
    mapping(uint256 => address) public nullifierHolder;
    mapping(address => uint256) public nonces;
    mapping(address => uint256) public deposits;
    uint256 private unlocked = 1;

    error ZeroAddress();
    error MissingContract();
    error InvalidPolicy();
    error WrongMode();
    error WrongHolder();
    error InvalidAmount();
    error InvalidNonce();
    error CredentialExpired();
    error CredentialNotYetValid();
    error CredentialRevoked();
    error Ineligible();
    error WrongPolicyVersion();
    error InvalidSignatureLength();
    error InvalidSignature();
    error InactiveIssuer();
    error InvalidPublicSignals();
    error InvalidWindow();
    error InvalidProof();
    error NullifierAlreadyBound();
    error CacheDisabled();
    error NoCachedAuthorization();
    error StaleAuthorization();
    error AuthorizationExpired();
    error TokenTransferFailed();
    error Reentrancy();

    event Authorized(address indexed holder, uint256 indexed nullifier, uint64 until, uint256 context);
    event Deposited(address indexed holder, uint256 amount, uint256 nonce, bool cached);

    constructor(address registry_, address token_, address verifier_, bool zkMode_, bool cacheEnabled_,
        uint8 policyMode_, uint64 deltaSeconds_, uint64 rootGraceSeconds_)
    {
        if (registry_ == address(0) || token_ == address(0)) revert ZeroAddress();
        if (registry_.code.length == 0 || token_.code.length == 0) revert MissingContract();
        if (zkMode_) {
            if (verifier_ == address(0)) revert ZeroAddress();
            if (verifier_.code.length == 0) revert MissingContract();
        }
        if (policyMode_ > 2 || deltaSeconds_ > 1 days || rootGraceSeconds_ > 1 days ||
            (policyMode_ != 2 && deltaSeconds_ != 0) || (policyMode_ == 0 && rootGraceSeconds_ != 0)) {
            revert InvalidPolicy();
        }
        registry = IPolicyRegistry(registry_);
        token = IPolicyDepositToken(token_);
        verifier = IPolicyVerifier(verifier_);
        zkMode = zkMode_;
        cacheEnabled = cacheEnabled_;
        policyMode = policyMode_;
        deltaSeconds = deltaSeconds_;
        rootGraceSeconds = rootGraceSeconds_;
    }

    modifier nonReentrant() {
        if (unlocked != 1) revert Reentrancy();
        unlocked = 2;
        _;
        unlocked = 1;
    }

    function domainSeparator() public view returns (bytes32) {
        return keccak256(abi.encode(DOMAIN_TYPEHASH, keccak256("PETs4DeFiEligibility"),
            keccak256("2"), block.chainid, address(registry)));
    }

    function hashCredential(Credential calldata credential) public view returns (bytes32) {
        bytes32 structHash = keccak256(abi.encode(CREDENTIAL_TYPEHASH, credential.holder,
            credential.id, credential.policyVersion, credential.validFrom, credential.validUntil,
            credential.eligible));
        return keccak256(abi.encodePacked("\x19\x01", domainSeparator(), structHash));
    }

    function computeScope() public view returns (uint256) {
        return uint256(keccak256(abi.encode(block.chainid, address(this), POLICY_ID))) % SNARK_FIELD;
    }

    function computeRequestHash(address holder, uint256 amount, uint256 nonce,
        uint64 windowStart, uint64 windowEnd) public view returns (uint256)
    {
        return computeRequestHashForRoot(registry.registryRoot(), holder, amount, nonce, windowStart, windowEnd);
    }

    /// @dev Selective presentations bind to their accepted root's security
    /// context, not a publication counter which changes on unrelated additions.
    function computeRequestHashForRoot(uint256 root, address holder, uint256 amount,
        uint256 nonce, uint64 windowStart, uint64 windowEnd) public view returns (uint256)
    {
        (uint256 epoch_, , bool exists) = registry.roots(root);
        if (!exists) revert InvalidPublicSignals();
        uint256 context = policyMode == 0 ? registry.publicationEpoch() : epoch_;
        bytes32 action = keccak256(abi.encode(block.chainid, address(this), holder,
            address(token), amount, nonce));
        return uint256(keccak256(abi.encode(action, root, context, windowStart, windowEnd))) & REQUEST_MASK;
    }

    function depositSigned(Credential calldata credential, bytes calldata signature, uint256 amount, uint256 nonce)
        external nonReentrant
    {
        if (zkMode) revert WrongMode();
        _checkAction(amount, nonce);
        if (credential.holder != msg.sender) revert WrongHolder();
        if (block.timestamp < credential.validFrom) revert CredentialNotYetValid();
        if (block.timestamp >= credential.validUntil) revert CredentialExpired();
        if (credential.policyVersion != registry.policyVersion()) revert WrongPolicyVersion();
        address issuer = _recover(hashCredential(credential), signature);
        uint64 statusDeadline = _checkSignedStatus(issuer, credential.id);
        if (!credential.eligible) revert Ineligible();
        uint256 ttlEnd = block.timestamp + registry.maxTTL();
        uint64 until = ttlEnd < credential.validUntil ? uint64(ttlEnd) : credential.validUntil;
        if (statusDeadline < until) until = statusDeadline;
        if (cacheEnabled) {
            // Independent signed caches need no changing ZK publication or
            // security epoch. Only the global treatment stores publication.
            uint256 publication = policyMode == 0 ? registry.publicationEpoch() : 0;
            caches[msg.sender] = Authorization(until, publication, 0, 0, issuer,
                credential.id, credential.policyVersion);
            emit Authorized(msg.sender, 0, until, publication);
        }
        _completeDeposit(amount, nonce, false);
    }

    function depositZK(Proof calldata proof, uint256 amount, uint256 nonce) external nonReentrant {
        if (!zkMode) revert WrongMode();
        _checkAction(amount, nonce);
        (uint256 epoch_, uint64 securityLimit) = _checkProofContext(proof.publicSignals, amount, nonce);
        if (!verifier.verifyProof(proof.a, proof.b, proof.c, proof.publicSignals)) revert InvalidProof();
        uint256 nullifier = proof.publicSignals[0];
        address boundHolder = nullifierHolder[nullifier];
        if (boundHolder != address(0) && boundHolder != msg.sender) revert NullifierAlreadyBound();
        if (boundHolder == address(0)) nullifierHolder[nullifier] = msg.sender;
        if (cacheEnabled) {
            uint64 until = uint64(proof.publicSignals[5]);
            if (securityLimit < until) until = securityLimit;
            uint256 publication = policyMode == 0 ? registry.publicationEpoch() : 0;
            // Preserve OLD proof epoch during grace; assigning current epoch
            // here would permit an old revoked proof to revive authorization.
            uint256 cachedEpoch = policyMode == 0 ? 0 : epoch_;
            caches[msg.sender] = Authorization(until, publication, cachedEpoch,
                nullifier, address(0), 0, 0);
            emit Authorized(msg.sender, nullifier, until, policyMode == 0 ? publication : epoch_);
        }
        _completeDeposit(amount, nonce, false);
    }

    function depositCached(uint256 amount, uint256 nonce) external nonReentrant {
        if (!cacheEnabled) revert CacheDisabled();
        _checkAction(amount, nonce);
        Authorization storage auth = caches[msg.sender];
        if (auth.until == 0) revert NoCachedAuthorization();
        if (block.timestamp >= auth.until) revert AuthorizationExpired();
        if (policyMode == 0) {
            if (auth.publicationEpoch != registry.publicationEpoch()) revert StaleAuthorization();
        } else if (zkMode) {
            (bool ok, ) = registry.securityDeadline(auth.securityEpoch, deltaSeconds);
            if (!ok) revert StaleAuthorization();
        }
        if (!zkMode) {
            if (auth.policyVersion != registry.policyVersion()) revert WrongPolicyVersion();
            _checkSignedStatus(auth.issuer, auth.credentialId);
        }
        _completeDeposit(amount, nonce, true);
    }

    function _checkSignedStatus(address issuer, uint256 id) private view returns (uint64 deadline) {
        if (!registry.isIssuerActive(issuer)) revert InactiveIssuer();
        uint64 revokedTimestamp = registry.revokedAt(issuer, id);
        if (revokedTimestamp == 0) return type(uint64).max;
        deadline = revokedTimestamp + deltaSeconds;
        if (block.timestamp >= deadline) revert CredentialRevoked();
    }

    function _checkProofContext(uint256[8] calldata s, uint256 amount, uint256 nonce)
        private view returns (uint256 epoch_, uint64 securityLimit)
    {
        for (uint256 i; i < 8; ++i) if (s[i] >= SNARK_FIELD) revert InvalidPublicSignals();
        if (s[2] != registry.policyRoot() || s[3] != registry.minTier() || s[6] != computeScope()) {
            revert InvalidPublicSignals();
        }
        if (policyMode == 0) {
            if (s[1] != registry.registryRoot()) revert InvalidPublicSignals();
            epoch_ = registry.securityEpoch();
            securityLimit = type(uint64).max;
        } else {
            (bool accepted, uint256 rootEpoch, ) = registry.acceptedRoot(s[1], deltaSeconds, rootGraceSeconds);
            if (!accepted) revert InvalidPublicSignals();
            epoch_ = rootEpoch;
            (bool valid, uint64 deadline) = registry.securityDeadline(epoch_, deltaSeconds);
            if (!valid) revert InvalidPublicSignals();
            securityLimit = deadline;
        }
        if (s[4] > type(uint64).max || s[5] > type(uint64).max || s[4] > block.timestamp ||
            s[5] <= block.timestamp || s[5] <= s[4] || s[5] - s[4] > registry.maxTTL()) {
            revert InvalidWindow();
        }
        if (s[7] != computeRequestHashForRoot(s[1], msg.sender, amount, nonce, uint64(s[4]), uint64(s[5]))) {
            revert InvalidPublicSignals();
        }
    }

    function _checkAction(uint256 amount, uint256 nonce) private view {
        if (amount == 0) revert InvalidAmount();
        if (nonce != nonces[msg.sender]) revert InvalidNonce();
    }

    function _recover(bytes32 digest, bytes calldata signature) private pure returns (address signer) {
        if (signature.length != 65) revert InvalidSignatureLength();
        bytes32 r;
        bytes32 s;
        uint8 v;
        assembly {
            r := calldataload(signature.offset)
            s := calldataload(add(signature.offset, 32))
            v := byte(0, calldataload(add(signature.offset, 64)))
        }
        if (uint256(s) > HALF_ORDER || (v != 27 && v != 28)) revert InvalidSignature();
        signer = ecrecover(digest, v, r, s);
        if (signer == address(0)) revert InvalidSignature();
    }

    function _completeDeposit(uint256 amount, uint256 nonce, bool cached) private {
        nonces[msg.sender] = nonce + 1;
        deposits[msg.sender] += amount;
        if (!token.transferFrom(msg.sender, address(this), amount)) revert TokenTransferFailed();
        emit Deposited(msg.sender, amount, nonce, cached);
    }
}
