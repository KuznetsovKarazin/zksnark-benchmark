pragma circom 2.0.0;

/*
Simple multiplication circuit for benchmarking.
Computes c = a * b and proves knowledge of inputs.
*/

template Multiply() {
    signal input a;
    signal input b;
    signal output c;
    
    c <== a * b;
}

component main = Multiply();