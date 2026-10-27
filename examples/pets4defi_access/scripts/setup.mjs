import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
process.chdir(root);
fs.mkdirSync('build', {recursive: true});
const cli = 'node_modules/snarkjs/cli.js';
const run = (args) => {
  console.log(`> ${args.slice(0, 5).join(' ')}`);
  const r = spawnSync(process.execPath, args, {stdio: 'inherit'});
  if (r.status !== 0) throw new Error(`Command failed: ${args.join(' ')}`);
};
const hash = (p) => crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const circuitHash = hash('circuits/eligible.circom');
const lockHash = hash('package-lock.json');
const previous = fs.existsSync('build/setup.json') ? JSON.parse(fs.readFileSync('build/setup.json')) : null;
const artifacts = {
  zkey_sha256: 'build/eligible_final.zkey',
  wasm_sha256: 'build/eligible_js/eligible.wasm',
  verifier_sha256: 'build/Verifier.sol',
  verification_key_sha256: 'build/verification_key.json',
};
if (previous?.circuit_sha256 === circuitHash && previous?.lock_sha256 === lockHash &&
    Object.entries(artifacts).every(([key,p]) => fs.existsSync(p) && previous[key] === hash(p))) {
  console.log('Reusing the matching LOCAL DEMO setup. It is not a production ceremony.');
  process.exit(0);
}
run(['node_modules/circom2/cli.js', 'circuits/eligible.circom', '--r1cs', '--wasm', '--sym',
     '--O2', '-l', 'node_modules', '-o', 'build']);
run([cli, 'r1cs', 'info', 'build/eligible.r1cs']);
run([cli, 'powersoftau', 'new', 'bn128', '10', 'build/pot0.ptau']);
run([cli, 'powersoftau', 'contribute', 'build/pot0.ptau', 'build/pot1.ptau',
     '--name=local-demo-only', `-e=${crypto.randomBytes(32).toString('hex')}`]);
run([cli, 'powersoftau', 'prepare', 'phase2', 'build/pot1.ptau', 'build/pot_final.ptau']);
run([cli, 'groth16', 'setup', 'build/eligible.r1cs', 'build/pot_final.ptau', 'build/eligible_0.zkey']);
run([cli, 'zkey', 'contribute', 'build/eligible_0.zkey', 'build/eligible_final.zkey',
     '--name=local-demo-only', `-e=${crypto.randomBytes(32).toString('hex')}`]);
run([cli, 'zkey', 'verify', 'build/eligible.r1cs', 'build/pot_final.ptau', 'build/eligible_final.zkey']);
run([cli, 'zkey', 'export', 'verificationkey', 'build/eligible_final.zkey', 'build/verification_key.json']);
run([cli, 'zkey', 'export', 'solidityverifier', 'build/eligible_final.zkey', 'build/Verifier.sol']);
fs.writeFileSync('build/setup.json', JSON.stringify({
  circuit_sha256: circuitHash, lock_sha256: lockHash,
  zkey_sha256: hash('build/eligible_final.zkey'),
  wasm_sha256: hash('build/eligible_js/eligible.wasm'),
  verifier_sha256: hash('build/Verifier.sol'),
  verification_key_sha256: hash('build/verification_key.json'),
  setup_status: 'single-process local demonstration; NOT a production trusted setup',
  created_utc: new Date().toISOString()
}, null, 2));
