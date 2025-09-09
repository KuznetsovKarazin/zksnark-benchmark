pragma circom 2.0.0;

include "../../node_modules/circomlib/circuits/poseidon.circom";

/*
Poseidon hash circuit for benchmarking.
Computes Poseidon hash of 2 inputs.
*/

template PoseidonHash2() {
    signal input in[2];
    signal output out;
    
    component hasher = Poseidon(2);
    hasher.inputs[0] <== in[0];
    hasher.inputs[1] <== in[1];
    
    out <== hasher.out;
}

component main = PoseidonHash2();