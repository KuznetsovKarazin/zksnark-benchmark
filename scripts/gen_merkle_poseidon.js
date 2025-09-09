// scripts/gen_merkle_poseidon.js
// Usage: node scripts/gen_merkle_poseidon.js <depth> <leafIndex>
//
// Outputs JSON:
// {
//   "leaf": "<dec>",
//   "pathElements": ["<dec>", ...], // length = depth
//   "pathIndex": [0|1, ...],        // length = depth
//   "root": "<dec>"
// }

const { buildPoseidon } = require("circomlibjs");
const crypto = require("crypto");

(async () => {
  const depth = parseInt(process.argv[2] || "16", 10);
  const leafIndex = parseInt(process.argv[3] || "0", 10);

  const poseidon = await buildPoseidon();
  const F = poseidon.F;

  // Robust coercion to BigInt, regardless of the internal type returned by circomlibjs/ffjavascript
  const toBig = (x) => {
    if (typeof x === "bigint") return x;
    // Try circomlib field hook if present
    if (F && typeof F.toObject === "function") {
      try {
        const y = F.toObject(x);
        if (typeof y === "bigint") return y;
      } catch (_) {}
    }
    // Uint8Array / Buffer / typed array -> hex -> BigInt
    if (x && typeof x === "object" && typeof x.length === "number") {
      const hex = Buffer.from(x).toString("hex") || "0";
      return BigInt("0x" + hex);
    }
    if (typeof x === "number") {
      if (!Number.isInteger(x)) throw new Error("Non-integer number");
      return BigInt(x);
    }
    if (typeof x === "string") {
      // Allow "0x..." or decimal
      return BigInt(x);
    }
    throw new Error("Unsupported element type: " + (typeof x));
  };

  // Field-safe random element: reduce 256-bit random to BN254 prime
  const randFr = () => {
    const x = BigInt("0x" + crypto.randomBytes(32).toString("hex"));
    return x % F.p;
  };

  const nLeaves = 1 << depth;
  if (leafIndex < 0 || leafIndex >= nLeaves) {
    throw new Error(`leafIndex must be in [0, ${nLeaves - 1}]`);
  }

  // Level 0: random leaves (BigInt)
  const leaves = Array.from({ length: nLeaves }, randFr);

  // Build tree levels as BigInts
  const levels = [leaves];
  let idx = leafIndex;
  const pathElements = [];
  const pathIndex = [];

  for (let i = 0; i < depth; i++) {
    const level = levels[i];
    const next = new Array(level.length / 2);

    for (let j = 0; j < level.length; j += 2) {
      const left = toBig(level[j]);
      const right = toBig(level[j + 1]);
      const h = toBig(poseidon([left, right])); // force to BigInt
      next[j / 2] = h;
    }

    pathIndex.push(idx & 1);           // 0 => cur is left, 1 => cur is right
    pathElements.push(toBig(level[idx ^ 1])); // sibling (BigInt)
    levels.push(next);
    idx >>= 1;
  }

  const root = toBig(levels[depth][0]);
  const leaf = toBig(leaves[leafIndex]);

  const toDec = (x) => toBig(x).toString();

  process.stdout.write(
    JSON.stringify({
      leaf: toDec(leaf),
      pathElements: pathElements.map(toDec),
      pathIndex: pathIndex, // integers 0/1
      root: toDec(root),
    })
  );
})();
