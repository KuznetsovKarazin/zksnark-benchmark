pragma circom 2.1.6;

include "circomlib/circuits/poseidon.circom";
include "circomlib/circuits/bitify.circom";

// Binary Merkle with Poseidon; inputs match your runner.
template MerklePoseidonBinary(DEPTH) {
    signal input leaf;
    signal input pathElements[DEPTH];
    signal input pathIndex[DEPTH];   // 0 or 1
    signal input root;               // provided by runner
    signal output outRoot;           // computed root

    component nb[DEPTH];
    component H[DEPTH];

    signal s[DEPTH];
    signal acc[DEPTH + 1];

    signal l0[DEPTH]; signal l1[DEPTH]; signal left[DEPTH];
    signal r0[DEPTH]; signal r1[DEPTH]; signal right[DEPTH];

    acc[0] <== leaf;

    for (var i = 0; i < DEPTH; i++) {
        nb[i] = Num2Bits(1);
        nb[i].in <== pathIndex[i];
        s[i] <== nb[i].out[0];

        l0[i]    <== (1 - s[i]) * acc[i];
        l1[i]    <== s[i] * pathElements[i];
        left[i]  <== l0[i] + l1[i];

        r0[i]    <== s[i] * acc[i];
        r1[i]    <== (1 - s[i]) * pathElements[i];
        right[i] <== r0[i] + r1[i];

        H[i] = Poseidon(2);
        H[i].inputs[0] <== left[i];
        H[i].inputs[1] <== right[i];

        acc[i + 1] <== H[i].out;
    }

    outRoot <== acc[DEPTH];

    // To enforce equality with provided root, uncomment:
    // outRoot == root;
}

component main { public [ root ] } = MerklePoseidonBinary(4);
