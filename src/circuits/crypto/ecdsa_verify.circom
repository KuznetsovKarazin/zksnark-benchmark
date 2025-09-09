// src/circuits/crypto/ecdsa_verify.circom
pragma circom 2.1.9;

include "circomlib/circuits/bitify.circom";
include "ecdsa.circom"; // from vendor/circom-ecdsa/circuits

// 32 bytes (big-endian) -> 256 bits (little-endian)
template Bytes32BE_to_Bits256LE() {
    signal input  in[32];
    signal output out[256];

    component b2[32];
    for (var i = 0; i < 32; i++) {
        b2[i] = Num2Bits(8);
        b2[i].in <== in[i];
    }
    for (var i = 0; i < 32; i++) {
        var src = 31 - i;
        for (var j = 0; j < 8; j++) {
            out[i*8 + j] <== b2[src].out[j];
        }
    }
}

// 256 bits (LE) -> 4 limbs of 64 bits (LE)
template Bits256LE_to_U64x4LE() {
    signal input  bits[256];
    signal output limbs[4];

    component n[4];
    for (var i = 0; i < 4; i++) {
        n[i] = Bits2Num(64);
        for (var j = 0; j < 64; j++) {
            n[i].in[j] <== bits[i*64 + j];
        }
        limbs[i] <== n[i].out;
    }
}

template ECDSA_Wrapper() {
    // All 32-byte big-endian
    signal input msg[32];
    signal input pubKeyX[32];
    signal input pubKeyY[32];
    signal input r[32];
    signal input s[32];

    // Public flag to assert verification result
    signal input expect_ok;
    signal output ok;

    // Byte -> bits
    component cm = Bytes32BE_to_Bits256LE();
    component cx = Bytes32BE_to_Bits256LE();
    component cy = Bytes32BE_to_Bits256LE();
    component cr = Bytes32BE_to_Bits256LE();
    component cs = Bytes32BE_to_Bits256LE();

    for (var i = 0; i < 32; i++) {
        cm.in[i] <== msg[i];
        cx.in[i] <== pubKeyX[i];
        cy.in[i] <== pubKeyY[i];
        cr.in[i] <== r[i];
        cs.in[i] <== s[i];
    }

    // bits -> u64 limbs
    component lm = Bits256LE_to_U64x4LE();
    component lx = Bits256LE_to_U64x4LE();
    component ly = Bits256LE_to_U64x4LE();
    component lr = Bits256LE_to_U64x4LE();
    component ls = Bits256LE_to_U64x4LE();

    for (var k = 0; k < 256; k++) {
        lm.bits[k] <== cm.out[k];
        lx.bits[k] <== cx.out[k];
        ly.bits[k] <== cy.out[k];
        lr.bits[k] <== cr.out[k];
        ls.bits[k] <== cs.out[k];
    }

    // ECDSA verify: params order is (n, k) -> (64, 4) for 256-bit split
    component ver = ECDSAVerifyNoPubkeyCheck(64, 4);

    for (var t = 0; t < 4; t++) {
        ver.msghash[t]  <== lm.limbs[t];
        ver.r[t]        <== lr.limbs[t];
        ver.s[t]        <== ls.limbs[t];
        ver.pubkey[0][t] <== lx.limbs[t];
        ver.pubkey[1][t] <== ly.limbs[t];
    }

    ok <== ver.result;
    ok === expect_ok; // enforce expected result as a constraint
}

// Only expect_ok is public 
component main { public [ expect_ok ] } = ECDSA_Wrapper();
