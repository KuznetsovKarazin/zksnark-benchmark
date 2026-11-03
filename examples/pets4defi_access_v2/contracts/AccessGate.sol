// SPDX-License-Identifier: MIT
pragma solidity 0.8.37;

interface IEligibilityRegistry {
    function registryRoot() external view returns (uint256);
    function policyRoot() external view returns (uint256);
    function minTier() external view returns (uint256);
    function maxTTL() external view returns (uint64);
    function policyVersion() external view returns (uint256);
    function epoch() external view returns (uint256);
    function isIssuerActive(address issuer) external view returns (bool);
    function revoked(address issuer, uint256 id) external view returns (bool);
}

interface IDepositToken {
    function transferFrom(address sender, address recipient, uint256 amount) external returns (bool);
}

interface IEligibilityVerifier {
    function verifyProof(
        uint256[2] calldata a, uint256[2][2] calldata b,
        uint256[2] calldata c, uint256[8] calldata publicSignals
    ) external view returns (bool);
}

/// @notice Synthetic eligibility gate with matched direct/cached authorization.
/// @dev This is not legal KYC, a lending protocol, or a production deployment.
///      A scope nullifier links actions in one application; wallets and token
///      movements remain public. Holder-secret sharing is not prevented.
contract AccessGate {
    uint256 public constant SNARK_FIELD =
        21888242871839275222246405745257275088548364400416034343698204186575808495617;
    uint256 public constant REQUEST_MASK = (uint256(1) << 248) - 1;
    uint256 public constant POLICY_ID = 1;
    uint256 private constant HALF_ORDER =
        0x7fffffffffffffffffffffffffffffff5d576e7357a4501ddfe92f46681b20a0;
    bytes32 private constant DOMAIN_TYPEHASH = keccak256(
        "EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"
    );
    bytes32 public constant CREDENTIAL_TYPEHASH = keccak256(
        "Credential(address holder,uint256 id,uint256 policyVersion,uint64 validFrom,uint64 validUntil,bool eligible)"
    );

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
        uint256 epoch;
        uint256 nullifier;
    }

    IEligibilityRegistry public immutable registry;
    IDepositToken public immutable token;
    IEligibilityVerifier public immutable verifier;
    bool public immutable zkMode;
    bool public immutable cacheEnabled;
    mapping(address => Authorization) public caches;
    mapping(uint256 => address) public nullifierHolder;
    mapping(address => uint256) public nonces;
    mapping(address => uint256) public deposits;
    uint256 private unlocked = 1;

    error ZeroAddress();
    error MissingContract();
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

    event Authorized(address indexed holder, uint256 indexed nullifier, uint64 until, uint256 epoch);
    event Deposited(address indexed holder, uint256 amount, uint256 nonce, bool cached);

    constructor(address registry_, address token_, address verifier_, bool zkMode_, bool cacheEnabled_) {
        if (registry_ == address(0) || token_ == address(0)) revert ZeroAddress();
        if (registry_.code.length == 0 || token_.code.length == 0) revert MissingContract();
        if (zkMode_) {
            if (verifier_ == address(0)) revert ZeroAddress();
            if (verifier_.code.length == 0) revert MissingContract();
        }
        registry = IEligibilityRegistry(registry_);
        token = IDepositToken(token_);
        verifier = IEligibilityVerifier(verifier_);
        zkMode = zkMode_;
        cacheEnabled = cacheEnabled_;
    }

    modifier nonReentrant() {
        if (unlocked != 1) revert Reentrancy();
        unlocked = 2;
        _;
        unlocked = 1;
    }

    /// @notice Signed credentials are reusable across gates sharing this registry.
    function domainSeparator() public view returns (bytes32) {
        return keccak256(abi.encode(
            DOMAIN_TYPEHASH, keccak256("PETs4DeFiEligibility"), keccak256("2"),
            block.chainid, address(registry)
        ));
    }

    function hashCredential(Credential calldata credential) public view returns (bytes32) {
        bytes32 structHash = keccak256(abi.encode(
            CREDENTIAL_TYPEHASH, credential.holder, credential.id,
            credential.policyVersion, credential.validFrom, credential.validUntil, credential.eligible
        ));
        return keccak256(abi.encodePacked("\x19\x01", domainSeparator(), structHash));
    }

    function computeScope() public view returns (uint256) {
        return uint256(keccak256(abi.encode(block.chainid, address(this), POLICY_ID))) % SNARK_FIELD;
    }

    function computeRequestHash(
        address holder, uint256 amount, uint256 nonce, uint64 windowStart, uint64 windowEnd
    ) public view returns (uint256) {
        return uint256(keccak256(abi.encode(
            block.chainid, address(this), holder, address(token), amount, nonce,
            registry.epoch(), windowStart, windowEnd
        ))) & REQUEST_MASK;
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
        if (!registry.isIssuerActive(issuer)) revert InactiveIssuer();
        if (registry.revoked(issuer, credential.id)) revert CredentialRevoked();
        if (!credential.eligible) revert Ineligible();
        uint256 ttlEnd = block.timestamp + registry.maxTTL();
        uint64 until = ttlEnd < credential.validUntil ? uint64(ttlEnd) : credential.validUntil;
        _cache(until, 0);
        _completeDeposit(amount, nonce, false);
    }

    function depositZK(Proof calldata proof, uint256 amount, uint256 nonce) external nonReentrant {
        if (!zkMode) revert WrongMode();
        _checkAction(amount, nonce);
        _checkProofContext(proof.publicSignals, amount, nonce);
        if (!verifier.verifyProof(proof.a, proof.b, proof.c, proof.publicSignals)) revert InvalidProof();
        uint256 nullifier = proof.publicSignals[0];
        address boundHolder = nullifierHolder[nullifier];
        if (boundHolder != address(0) && boundHolder != msg.sender) revert NullifierAlreadyBound();
        // Bind before transfer; any failure rolls back this binding and the cache.
        if (boundHolder == address(0)) nullifierHolder[nullifier] = msg.sender;
        _cache(uint64(proof.publicSignals[5]), nullifier);
        _completeDeposit(amount, nonce, false);
    }

    function depositCached(uint256 amount, uint256 nonce) external nonReentrant {
        if (!cacheEnabled) revert CacheDisabled();
        _checkAction(amount, nonce);
        Authorization memory auth = caches[msg.sender];
        if (auth.until == 0) revert NoCachedAuthorization();
        if (auth.epoch != registry.epoch()) revert StaleAuthorization();
        if (block.timestamp >= auth.until) revert AuthorizationExpired();
        _completeDeposit(amount, nonce, true);
    }

    function _checkProofContext(uint256[8] calldata s, uint256 amount, uint256 nonce) private view {
        for (uint256 i; i < 8; ++i) if (s[i] >= SNARK_FIELD) revert InvalidPublicSignals();
        if (
            s[1] != registry.registryRoot() || s[2] != registry.policyRoot() ||
            s[3] != registry.minTier() || s[6] != computeScope()
        ) revert InvalidPublicSignals();
        if (
            s[4] > type(uint64).max || s[5] > type(uint64).max ||
            s[4] > block.timestamp || s[5] <= block.timestamp ||
            s[5] <= s[4] || s[5] - s[4] > registry.maxTTL()
        ) revert InvalidWindow();
        if (s[7] != computeRequestHash(msg.sender, amount, nonce, uint64(s[4]), uint64(s[5]))) {
            revert InvalidPublicSignals();
        }
    }

    function _checkAction(uint256 amount, uint256 nonce) private view {
        if (amount == 0) revert InvalidAmount();
        if (nonce != nonces[msg.sender]) revert InvalidNonce();
    }

    function _cache(uint64 until, uint256 nullifier) private {
        if (!cacheEnabled) return;
        uint256 currentEpoch = registry.epoch();
        caches[msg.sender] = Authorization(until, currentEpoch, nullifier);
        emit Authorized(msg.sender, nullifier, until, currentEpoch);
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
