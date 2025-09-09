// src/circuits/crypto/merkle_poseidon.circom
pragma circom 2.1.9;

// IMPORTANT:
// Pass "-l node_modules" to circom so that "circomlib/..." resolves.
// Do NOT write "node_modules/circomlib/..."; the include path already points there.
include "circomlib/circuits/poseidon.circom";
include "circomlib/circuits/comparators.circom";

/**
 * Merkle proof over Poseidon(2).
 *
 * Inputs:
 *  - leaf              : private leaf value
 *  - pathElements[i]   : private sibling at level i
 *  - pathIndex[i]      : private selector {0,1} at level i
 *                        0 -> (left = cur,  right = pathElements[i])
 *                        1 -> (left = pathElements[i], right = cur)
 *  - root              : expected Merkle root (public)
 *
 * Outputs:
 *  - computedRoot      : computed Merkle root
 *  - ok                : 1 if computedRoot == root, else 0
 *
 * Notes:
 *  - No "sum of products" in a single constraint (avoids T3001).
 *  - Signals are declared outside loops (avoids T2011).
 */
template MerklePoseidon(depth) {
    // --- inputs ---
    signal input leaf;
    signal input pathElements[depth];
    signal input pathIndex[depth];
    signal input root;

    // --- outputs ---
    signal output computedRoot;
    signal output ok;

    // --- predeclare signals used inside the loop as arrays ---
    signal tL[depth];       // sel * (pathEl - cur)
    signal tR[depth];       // sel * (cur - pathEl)
    signal left[depth];     // selected left
    signal right[depth];    // selected right
    signal cur[depth + 1];  // cur[0] = leaf; cur[i+1] = hash(left[i], right[i])

    // hashers for each level
    component H[depth];

    // initialize current hash with the leaf
    cur[0] <== leaf;

    // walk up the tree
    for (var i = 0; i < depth; i++) {
        // (1) enforce booleanity: pathIndex[i] ∈ {0,1}
        pathIndex[i] * (1 - pathIndex[i]) === 0;

        // (2) linear multiplexing without "sum of products":
        //     left  = cur + sel * (pathEl - cur)
        //     right = pathEl + sel * (cur - pathEl)
        tL[i]   <== pathIndex[i] * (pathElements[i] - cur[i]);  // single product
        tR[i]   <== pathIndex[i] * (cur[i] - pathElements[i]);  // single product
        left[i]  <== cur[i] + tL[i];                             // linear
        right[i] <== pathElements[i] + tR[i];                    // linear

        // (3) Poseidon(2) hash of the ordered pair
        H[i] = Poseidon(2);
        H[i].inputs[0] <== left[i];
        H[i].inputs[1] <== right[i];
        cur[i + 1] <== H[i].out;
    }

    computedRoot <== cur[depth];

    // (4) ok := (computedRoot == root)
    component eq = IsEqual();
    eq.in[0] <== computedRoot;
    eq.in[1] <== root;
    ok <== eq.out;
}

// Choose desired depth here (e.g., 16).
// IMPORTANT: declare root as public input.
component main { public [root] } = MerklePoseidon(16);
