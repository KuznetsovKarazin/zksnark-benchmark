// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IAccessToken {
    function transferFrom(address sender, address recipient, uint256 amount)
        external
        returns (bool);
}

interface IAccessGroth16Verifier {
    function verifyProof(
        uint256[2] calldata a,
        uint256[2][2] calldata b,
        uint256[2] calldata c,
        uint256[3] calldata publicSignals
    ) external view returns (bool);
}

/// @notice Research-only deposit gate for synthetic credentials and test tokens.
/// @dev Deploy the same contract twice, with privateMode false and true.
///      The private mode verifies the issuer's ECDSA signature OUTSIDE the proof.
///      The proof establishes hidden age eligibility and commitment opening, not
///      legal KYC. A stable public commitment and holder address remain linkable.
///      There is no withdrawal, interest, real asset, or production setup here.
contract AccessGate {
    uint256 public constant SNARK_FIELD =
        21888242871839275222246405745257275088548364400416034343698204186575808495617;
    uint256 private constant SECP256K1_HALF_ORDER =
        0x7fffffffffffffffffffffffffffffff5d576e7357a4501ddfe92f46681b20a0;

    bytes32 private constant DOMAIN_TYPEHASH = keccak256(
        "EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"
    );
    bytes32 private constant NAME_HASH = keccak256("PETs4DeFiAccess");
    bytes32 private constant VERSION_HASH = keccak256("1");
    bytes32 public constant BASELINE_TYPEHASH = keccak256(
        "BaselineCredential(address holder,uint256 credentialId,uint64 validUntil,bool eligible)"
    );
    bytes32 public constant PRIVATE_TYPEHASH = keccak256(
        "PrivateCredential(address holder,uint256 credentialId,uint64 validUntil,uint256 commitment)"
    );

    struct BaselineCredential {
        address holder;
        uint256 credentialId;
        uint64 validUntil;
        bool eligible;
    }

    struct PrivateCredential {
        address holder;
        uint256 credentialId;
        uint64 validUntil;
        uint256 commitment;
    }

    struct Proof {
        uint256[2] a;
        uint256[2][2] b;
        uint256[2] c;
        // Exact Circom order: [actionBinding, commitment, requestHash].
        uint256[3] publicSignals;
    }

    address public immutable issuer;
    IAccessToken public immutable token;
    IAccessGroth16Verifier public immutable verifier;
    bool public immutable privateMode;

    mapping(uint256 => bool) public revoked;
    mapping(address => uint256) public nonces;
    mapping(address => uint256) public deposits;
    uint256 private unlocked = 1;

    error ZeroAddress();
    error MissingContract();
    error WrongMode();
    error NotIssuer();
    error WrongHolder();
    error CredentialExpired();
    error CredentialRevoked();
    error Ineligible();
    error InvalidAmount();
    error InvalidNonce();
    error InvalidSignatureLength();
    error InvalidSignature();
    error InvalidPublicSignals();
    error InvalidProof();
    error TokenTransferFailed();
    error Reentrancy();

    event CredentialRevocation(uint256 indexed credentialId);
    event Deposited(
        address indexed holder,
        uint256 indexed credentialId,
        uint256 amount,
        uint256 nonce,
        bool privateMode
    );

    constructor(address issuer_, address token_, address verifier_, bool zkMode_) {
        if (issuer_ == address(0) || token_ == address(0)) revert ZeroAddress();
        if (token_.code.length == 0) revert MissingContract();
        if (zkMode_) {
            if (verifier_ == address(0)) revert ZeroAddress();
            if (verifier_.code.length == 0) revert MissingContract();
        }
        issuer = issuer_;
        token = IAccessToken(token_);
        verifier = IAccessGroth16Verifier(verifier_);
        privateMode = zkMode_;
    }

    modifier nonReentrant() {
        if (unlocked != 1) revert Reentrancy();
        unlocked = 2;
        _;
        unlocked = 1;
    }

    /// @notice Credential IDs are issuer-wide within this gate, not per holder.
    /// @dev Revocation is permanent and must be applied to both comparison gates.
    function revokeCredential(uint256 credentialId) external {
        if (msg.sender != issuer) revert NotIssuer();
        revoked[credentialId] = true;
        emit CredentialRevocation(credentialId);
    }

    function domainSeparator() public view returns (bytes32) {
        return keccak256(abi.encode(
            DOMAIN_TYPEHASH, NAME_HASH, VERSION_HASH, block.chainid, address(this)
        ));
    }

    /// @return EIP-712 digest, including this chain and this gate's address.
    function hashBaselineCredential(BaselineCredential calldata credential)
        public view returns (bytes32)
    {
        return _typedDigest(keccak256(abi.encode(
            BASELINE_TYPEHASH,
            credential.holder,
            credential.credentialId,
            credential.validUntil,
            credential.eligible
        )));
    }

    /// @return EIP-712 digest, including this chain and this gate's address.
    function hashPrivateCredential(PrivateCredential calldata credential)
        public view returns (bytes32)
    {
        return _typedDigest(keccak256(abi.encode(
            PRIVATE_TYPEHASH,
            credential.holder,
            credential.credentialId,
            credential.validUntil,
            credential.commitment
        )));
    }

    function computeRequestHash(
        address holder,
        uint256 amount,
        uint256 nonce,
        uint256 credentialId,
        uint64 validUntil
    ) public view returns (uint256) {
        return uint256(keccak256(abi.encode(
            block.chainid,
            address(this),
            holder,
            address(token),
            amount,
            nonce,
            credentialId,
            validUntil
        ))) % SNARK_FIELD;
    }

    function depositBaseline(
        BaselineCredential calldata credential,
        bytes calldata signature,
        uint256 amount,
        uint256 nonce
    ) external nonReentrant {
        if (privateMode) revert WrongMode();
        _checkRequest(
            credential.holder, credential.credentialId, credential.validUntil, amount, nonce
        );
        _checkSignature(hashBaselineCredential(credential), signature);
        if (!credential.eligible) revert Ineligible();
        _completeDeposit(credential.credentialId, amount, nonce);
    }

    function depositPrivate(
        PrivateCredential calldata credential,
        bytes calldata signature,
        uint256 amount,
        uint256 nonce,
        Proof calldata proof
    ) external nonReentrant {
        if (!privateMode) revert WrongMode();
        _checkRequest(
            credential.holder, credential.credentialId, credential.validUntil, amount, nonce
        );
        _checkSignature(hashPrivateCredential(credential), signature);
        if (
            credential.commitment >= SNARK_FIELD ||
            proof.publicSignals[0] >= SNARK_FIELD ||
            proof.publicSignals[1] != credential.commitment ||
            proof.publicSignals[2] != computeRequestHash(
                credential.holder, amount, nonce, credential.credentialId, credential.validUntil
            )
        ) revert InvalidPublicSignals();
        if (!verifier.verifyProof(proof.a, proof.b, proof.c, proof.publicSignals)) {
            revert InvalidProof();
        }
        _completeDeposit(credential.credentialId, amount, nonce);
    }

    function _checkRequest(
        address holder,
        uint256 credentialId,
        uint64 validUntil,
        uint256 amount,
        uint256 nonce
    ) private view {
        if (holder != msg.sender) revert WrongHolder();
        if (block.timestamp >= validUntil) revert CredentialExpired();
        if (revoked[credentialId]) revert CredentialRevoked();
        if (amount == 0) revert InvalidAmount();
        if (nonce != nonces[msg.sender]) revert InvalidNonce();
    }

    function _typedDigest(bytes32 structHash) private view returns (bytes32) {
        return keccak256(abi.encodePacked("\x19\x01", domainSeparator(), structHash));
    }

    function _checkSignature(bytes32 digest, bytes calldata signature) private view {
        if (signature.length != 65) revert InvalidSignatureLength();
        bytes32 r;
        bytes32 s;
        uint8 v;
        assembly {
            r := calldataload(signature.offset)
            s := calldataload(add(signature.offset, 32))
            v := byte(0, calldataload(add(signature.offset, 64)))
        }
        if (uint256(s) > SECP256K1_HALF_ORDER || (v != 27 && v != 28)) {
            revert InvalidSignature();
        }
        address signer = ecrecover(digest, v, r, s);
        if (signer == address(0) || signer != issuer) revert InvalidSignature();
    }

    function _completeDeposit(uint256 credentialId, uint256 amount, uint256 nonce) private {
        // Effects occur before the external call; any failure rolls back all state.
        nonces[msg.sender] = nonce + 1;
        deposits[msg.sender] += amount;
        if (!token.transferFrom(msg.sender, address(this), amount)) {
            revert TokenTransferFailed();
        }
        emit Deposited(msg.sender, credentialId, amount, nonce, privateMode);
    }
}
