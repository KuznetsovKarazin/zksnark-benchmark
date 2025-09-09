// scripts/gen_ecdsa.js
// Usage: node scripts/gen_ecdsa.js <seed>
//
// Outputs JSON with 32-byte big-endian arrays:
// { msg, pubKeyX, pubKeyY, r, s }

const crypto = require("crypto");
const secp256k1 = require("secp256k1");

// deterministic 32 bytes from seed
function seedTo32(seedInt) {
  const buf = Buffer.alloc(32);
  buf.writeBigUInt64BE(BigInt(seedInt >>> 0), 24); // put seed in last 8 bytes
  return crypto.createHash("sha256").update(buf).digest(); // 32 bytes
}

function to32BE(bi) {
  // bi: BigInt 0..2^256-1
  let hex = bi.toString(16);
  if (hex.length % 2) hex = "0" + hex;
  const b = Buffer.from(hex, "hex");
  if (b.length > 32) return b.slice(-32);
  if (b.length === 32) return b;
  return Buffer.concat([Buffer.alloc(32 - b.length), b]);
}

function bufToArray(b) {
  return Array.from(b.values()); // integers 0..255
}

(async () => {
  const seed = parseInt(process.argv[2] || "42", 10);

  // 1) make a valid private key deterministically from seed
  let sk = seedTo32(seed);
  while (!secp256k1.privateKeyVerify(sk)) {
    sk = crypto.createHash("sha256").update(sk).digest();
  }

  // 2) message: det hash from seed
  const msg = crypto.createHash("sha256").update(Buffer.from(`bench:${seed}`)).digest(); // 32 bytes

  // 3) sign (low-s normalized)
  const { signature } = secp256k1.ecdsaSign(msg, sk);
  const sigR = signature.slice(0, 32);
  const sigS = signature.slice(32, 64);

  // 4) public key (uncompressed)
  const pkUncomp = secp256k1.publicKeyCreate(sk, false); // 65 bytes: 0x04 || X(32) || Y(32)
  const pkX = pkUncomp.slice(1, 33);
  const pkY = pkUncomp.slice(33, 65);

  const out = {
      msg: bufToArray(msg),
      pubKeyX: bufToArray(pkX),
      pubKeyY: bufToArray(pkY),
      r: bufToArray(sigR),
      s: bufToArray(sigS),
      expect_ok: 1
  };


  process.stdout.write(JSON.stringify(out));
})();
