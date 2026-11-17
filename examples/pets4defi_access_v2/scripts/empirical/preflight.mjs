// Read-only public testnet readiness check. Does not request or print a secret.
import fs from 'node:fs';
import path from 'node:path';
import {ethers} from 'ethers';
const out=process.argv[2]??'../../projects/pets4defi/econ08/empirical_v03/results/testnet_preflight.json';
const url=process.env.ECON08_TESTNET_RPC??'https://sepolia.base.org';
const rpc=new ethers.JsonRpcProvider(url,undefined,{cacheTimeout:-1});
const report={checked_utc:new Date().toISOString(),broadcast:false,network_ready:false,signer_configured:Boolean(process.env.ECON08_TESTNET_PRIVATE_KEY),
  private_key_handling:'Environment variable only; never included in report',public_testnet_complete:false};
try {
  const net=await rpc.getNetwork();report.chain_id=net.chainId.toString();
  if(![84532n,11155420n].includes(net.chainId))throw Error('Unexpected chain; mainnet is forbidden');
  const latest=await rpc.getBlock('latest');report.latest_block={number:latest.number,hash:latest.hash,timestamp:latest.timestamp};
  report.network_ready=true;
  if(report.signer_configured) {
    const signer=new ethers.Wallet(process.env.ECON08_TESTNET_PRIVATE_KEY,rpc);
    report.funder=signer.address;report.balance_testeth=ethers.formatEther(await rpc.getBalance(signer.address));
  } else report.blocker='A funded disposable testnet signer must be configured locally before --broadcast. No public deployment has occurred.';
} catch(error) {report.error=error.shortMessage??error.message;}
fs.mkdirSync(path.dirname(out),{recursive:true});fs.writeFileSync(out,JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report));await rpc.destroy();
