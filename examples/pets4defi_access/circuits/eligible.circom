pragma circom 2.1.9;

include "circomlib/circuits/poseidon.circom";
include "circomlib/circuits/comparators.circom";

// Synthetic age eligibility. The issuer's secp256k1 signature is checked by
// AccessGate over this SAME public commitment and the credential metadata.
// This circuit alone does not authenticate an issuer or enforce revocation.
template Eligible() {
    signal input age;
    signal input salt;
    signal input commitment;
    signal input requestHash;
    signal output actionBinding;

    component ageBits = Num2Bits(8);
    ageBits.in <== age;
    component adult = LessThan(8);
    adult.in[0] <== 17;
    adult.in[1] <== age;
    adult.out === 1;

    component credentialHash = Poseidon(2);
    credentialHash.inputs[0] <== age;
    credentialHash.inputs[1] <== salt;
    commitment === credentialHash.out;

    // Use the request context in a non-linear constraint so changing the
    // chain/contract/holder/amount/nonce-bound request invalidates this proof.
    component bind = Poseidon(2);
    bind.inputs[0] <== salt;
    bind.inputs[1] <== requestHash;
    actionBinding <== bind.out;
}

// snarkjs signal order: actionBinding (output), commitment, requestHash.
component main {public [commitment, requestHash]} = Eligible();
