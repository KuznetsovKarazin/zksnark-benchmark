const { buildPoseidon } = require("circomlibjs");

(async () => {
  const poseidon = await buildPoseidon();
  const F = poseidon.F;
  const a = BigInt(process.argv[2] || "123");
  const b = BigInt(process.argv[3] || "456");
  const h = poseidon([a, b]);
  console.log(JSON.stringify({ 
    in: [a.toString(), b.toString()], 
    out: F.toString(h) 
  }));
})();