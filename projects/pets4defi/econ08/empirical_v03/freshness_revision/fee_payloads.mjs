// Replay-only unsigned EIP-1559 envelopes for historical Base GasPriceOracle.
import fs from 'node:fs';
import {gunzipSync} from 'node:zlib';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
const project = new URL('../../../../../examples/pets4defi_access_v2/package.json', import.meta.url);
const {Interface, Transaction} = createRequire(project)('ethers');
const folder = new URL('../results/evm_N32/', import.meta.url);
const read = name => JSON.parse(gunzipSync(fs.readFileSync(new URL(name, folder))));
const records = read('public_records.json.gz');
const classes = new Map(read('extracted.json.gz').map(x => [x.tx_hash,x]));
const oracle = new Interface(['function getL1Fee(bytes) view returns (uint256)']);
const rows = [];
for (const kind of ['full_zk','hit','publication']) {
  const candidates = records.filter(r => classes.get(r.transaction.hash).kind === kind && BigInt(r.receipt.status) === 1n);
  candidates.sort((a,b) => Number(BigInt(a.receipt.gasUsed) - BigInt(b.receipt.gasUsed)));
  const picks = kind === 'publication' ? candidates : [candidates[Math.floor(candidates.length/2)]];
  for (const r of picks) {
    const tx = r.transaction;
    const envelope = Transaction.from({type:2,chainId:8453,nonce:7,to:tx.to,data:tx.input,value:BigInt(tx.value),gasLimit:1000000n,maxFeePerGas:10000000000n,maxPriorityFeePerGas:0n,accessList:[]});
    rows.push({name:kind === 'publication' ? 'registry_'+r.receipt.gasUsed : kind,kind,gas_used:Number(BigInt(r.receipt.gasUsed)),local_tx_hash:tx.hash,serialized_unsigned_bytes:(envelope.unsignedSerialized.length-2)/2,oracle_calldata:oracle.encodeFunctionData('getL1Fee',[envelope.unsignedSerialized])});
  }
}
const heartbeat=JSON.parse(fs.readFileSync(new URL('./results/issuer_epochs.json',import.meta.url)));
for(const leg of heartbeat.gas.filter(v=>v.stage==='empty')) {
  const envelope=Transaction.from({type:2,chainId:8453,nonce:7,to:leg.to,data:leg.data,value:0n,gasLimit:1000000n,maxFeePerGas:10000000000n,maxPriorityFeePerGas:0n,accessList:[]});
  rows.push({name:'issuer_'+leg.position,kind:'issuer_heartbeat',gas_used:leg.gas,local_tx_hash:leg.local_tx_hash,serialized_unsigned_bytes:(envelope.unsignedSerialized.length-2)/2,oracle_calldata:oracle.encodeFunctionData('getL1Fee',[envelope.unsignedSerialized])});
}
fs.writeFileSync(fileURLToPath(new URL('./results/quote_templates.json',import.meta.url)),JSON.stringify(rows,null,2)+'\n');
