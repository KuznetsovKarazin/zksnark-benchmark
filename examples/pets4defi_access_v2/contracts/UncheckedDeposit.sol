// SPDX-License-Identifier: MIT
pragma solidity 0.8.37;

interface IUncheckedDepositToken {
    function transferFrom(address sender, address recipient, uint256 amount) external returns (bool);
}

/// @notice Matched deposit control without eligibility authorization.
contract UncheckedDeposit {
    IUncheckedDepositToken public immutable token;
    mapping(address => uint256) public nonces;
    mapping(address => uint256) public deposits;
    uint256 private unlocked = 1;
    error ZeroAddress();
    error MissingContract();
    error InvalidAmount();
    error InvalidNonce();
    error TokenTransferFailed();
    error Reentrancy();
    event Deposited(address indexed holder, uint256 amount, uint256 nonce, bool cached);

    constructor(address token_) {
        if (token_ == address(0)) revert ZeroAddress();
        if (token_.code.length == 0) revert MissingContract();
        token = IUncheckedDepositToken(token_);
    }

    modifier nonReentrant() {
        if (unlocked != 1) revert Reentrancy();
        unlocked = 2;
        _;
        unlocked = 1;
    }

    function deposit(uint256 amount, uint256 nonce) external nonReentrant {
        if (amount == 0) revert InvalidAmount();
        if (nonce != nonces[msg.sender]) revert InvalidNonce();
        nonces[msg.sender] = nonce + 1;
        deposits[msg.sender] += amount;
        if (!token.transferFrom(msg.sender, address(this), amount)) revert TokenTransferFailed();
        emit Deposited(msg.sender, amount, nonce, false);
    }
}
