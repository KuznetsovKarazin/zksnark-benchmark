// src/circuits/basic/range_proof.circom
pragma circom 2.1.6;

include "circomlib/circuits/bitify.circom";

// Доказать: 0 <= x < 2^N
template RangeProof(N) {
    assert(N > 0);
    signal input x;         // the number to prove
    signal output bits[N];  // convenient output: bit decomposition

    // This component itself guarantees: x == sum(bits[i]*2^i) and x < 2^N
    component n2b = Num2Bits(N);
    n2b.in <== x;

    // Forward bits to the output (assign each signal exactly once)
    for (var i = 0; i < N; i++) {
        bits[i] <== n2b.out[i];
    }
}

// You can change the bit depth if necessary
component main = RangeProof(32);
