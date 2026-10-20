// SPDX-License-Identifier: MIT
pragma solidity 0.8.37;

import "./MockToken.sol";

/// @notice Deliberately configurable adversary for local failure/reentry tests.
/// @dev Anyone may configure this TEST token; it is never an application asset.
contract AdversarialToken is MockToken {
    // 0 = transfer normally; 1 = return false; 2 = revert.
    uint8 public failureMode;
    address public reentryTarget;
    bytes public reentryData;
    bool public reentryEnabled;
    bool public propagateReentryFailure;
    bool public lastReentrySuccess;
    bytes public lastReentryResult;
    bool private inCallback;

    error InvalidFailureMode();
    error DeliberateTransferFailure();
    error ReentryCallFailed(bytes result);

    constructor(address initialHolder, uint256 initialSupply) MockToken(initialHolder, initialSupply) {}

    function setFailureMode(uint8 mode) external {
        if (mode > 2) revert InvalidFailureMode();
        failureMode = mode;
    }

    function setReentry(address target, bytes calldata data, bool enabled, bool propagateFailure) external {
        reentryTarget = target;
        reentryData = data;
        reentryEnabled = enabled;
        propagateReentryFailure = propagateFailure;
    }

    function transferFrom(address sender, address recipient, uint256 amount) public override returns (bool) {
        if (failureMode == 1) return false;
        if (failureMode == 2) revert DeliberateTransferFailure();
        if (reentryEnabled && !inCallback) {
            inCallback = true;
            (bool success, bytes memory result) = reentryTarget.call(reentryData);
            inCallback = false;
            lastReentrySuccess = success;
            lastReentryResult = result;
            if (!success && propagateReentryFailure) revert ReentryCallFailed(result);
        }
        return super.transferFrom(sender, recipient, amount);
    }
}
