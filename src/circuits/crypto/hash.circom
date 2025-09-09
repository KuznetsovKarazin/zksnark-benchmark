// src/circuits/crypto/hash.circom
pragma circom 2.1.6;

include "circomlib/circuits/mimcsponge.circom";

template HashMiMCSponge2(NROUNDS) {
    signal input in[2];
    signal output out;

    component S = MiMCSponge(2, NROUNDS, 1);
    S.k <== 0;                
    S.ins[0] <== in[0];
    S.ins[1] <== in[1];
    out      <== S.outs[0];
}

// ===== Option 1: without public signals =====
// component main = HashMiMCSponge2(220);

// ===== Option 2: Make EXACTLY the inputs public =====
component main { public [ in ] } = HashMiMCSponge2(220);


