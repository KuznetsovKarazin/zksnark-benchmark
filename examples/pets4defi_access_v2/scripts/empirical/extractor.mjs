// Public-data-only extractor. No harness imports, issuer assignments or witnesses.
import {Interface} from 'ethers';

export const gateABI = new Interface([
  'function depositZK((uint256[2] a,uint256[2][2] b,uint256[2] c,uint256[8] publicSignals) proof,uint256 amount,uint256 nonce)',
  'function depositSigned((address holder,uint256 id,uint256 policyVersion,uint64 validFrom,uint64 validUntil,bool eligible) credential,bytes signature,uint256 amount,uint256 nonce)',
  'function depositCached(uint256 amount,uint256 nonce)',
  'event Deposited(address indexed holder,uint256 amount,uint256 nonce,bool cached)',
]);
export const registryABI = new Interface([
  'event IssuerRootPublished(uint256 indexed issuerIndex,uint256 root,bool securityChange,uint256 publicationEpoch,uint256 securityEpoch)',
  'event BatchPublished(uint256 root,uint64 asOf,uint64 freshUntil,uint256 epoch)',
]);
const lower=x=>x?.toLowerCase();
const eq=(a,b)=>a!=null&&b!=null&&lower(String(a))===lower(String(b));
const dec=x=>BigInt(x).toString();
const sameInt=(a,b)=>a!=null&&b!=null&&BigInt(a)===BigInt(b);

export function fees(receipt,{chainType='unknown',operatorFeeModel='unknown'}={}) {
  const gas=BigInt(receipt.gasUsed);
  const price=receipt.effectiveGasPrice??receipt.gasPrice;
  const execution=price==null?null:gas*BigInt(price);
  const l1=chainType==='l1'?0n:(receipt.l1Fee==null?null:BigInt(receipt.l1Fee));
  let operator=null;
  if(chainType==='l1'||operatorFeeModel==='zero') operator=0n;
  else if(['isthmus','jovian'].includes(operatorFeeModel)) {
    // The caller must verify the chain's fork/configuration at this block.
    // Absent fields are unknown, not assumed zero.
    if(receipt.operatorFeeScalar!=null&&receipt.operatorFeeConstant!=null) {
      const s=BigInt(receipt.operatorFeeScalar),c=BigInt(receipt.operatorFeeConstant);
      operator=c+(operatorFeeModel==='isthmus'?gas*s/1000000n:gas*s*100n);
    }
  }
  const str=x=>x==null?null:x.toString();
  return {gas_used:gas.toString(),execution_wei:str(execution),l1_data_wei:str(l1),
    operator_wei:str(operator),total_wei:execution==null||l1==null||operator==null?null:str(execution+l1+operator),
    operator_fee_model:operatorFeeModel};
}

export function extract({transaction:tx,receipt:r,block},config) {
  if(!Array.isArray(config.gates)||!Array.isArray(config.registries)) throw Error('Explicit contract allowlists required');
  const hash=r.transactionHash??r.hash;
  if(!eq(tx.hash,hash)||!eq(tx.blockHash,r.blockHash)||!eq(r.blockHash,block.hash)||
     !sameInt(tx.blockNumber,r.blockNumber)||!sameInt(r.blockNumber,block.number)||
     !eq(tx.from,r.from)||lower(tx.to)!==lower(r.to)||!sameInt(tx.chainId,config.chainId)) throw Error('Inconsistent public record');
  for(const log of r.logs??[]) {
    if(!eq(log.transactionHash,hash)||!eq(log.blockHash,r.blockHash)||!sameInt(log.blockNumber,r.blockNumber)||log.removed) throw Error('Inconsistent event');
  }
  const out={tx_hash:hash,block_hash:block.hash,block_number:dec(block.number),timestamp:Number(BigInt(block.timestamp)),
    sender:lower(tx.from),to:lower(tx.to),selector:(tx.input??tx.data??'0x').slice(0,10),
    success:BigInt(r.status)===1n,kind:'other',fees:fees(r,config)};
  const data=tx.input??tx.data;
  if(config.gates.map(lower).includes(lower(tx.to))) {
    let call;try{call=gateABI.parseTransaction({data});}catch{call=null;}
    if(!call) return {...out,kind:'unsupported_gate_call'};
    const expected=call.name==='depositCached'?'hit':call.name==='depositZK'?'full_zk':'full_signed';
    if(!out.success) return {...out,kind:'reverted',attempt:expected};
    const events=(r.logs??[]).filter(x=>eq(x.address,tx.to)).map(x=>{try{return gateABI.parseLog(x);}catch{return null;}}).filter(x=>x?.name==='Deposited');
    if(events.length!==1) throw Error('Successful access must have exactly one matching Deposited event');
    const event=events[0].args;
    if(!eq(event.holder,tx.from)||event.amount!==call.args.amount||event.nonce!==call.args.nonce||event.cached!==(expected==='hit')) throw Error('Calldata/event disagreement');
    return {...out,kind:expected,amount:event.amount.toString(),nonce:event.nonce.toString()};
  }
  if(config.registries.map(lower).includes(lower(tx.to))&&out.success) {
    const events=(r.logs??[]).filter(x=>eq(x.address,tx.to)).map(x=>{try{return registryABI.parseLog(x);}catch{return null;}}).filter(Boolean);
    if(events.length>1) throw Error('Multiple registry publications need an explicit decoder');
    if(events.length===1) {
      const ev=events[0];
      return {...out,kind:'publication',publication_type:ev.name,
        public_issuer_index:ev.name==='IssuerRootPublished'?ev.args.issuerIndex.toString():null,
        root:ev.args.root.toString()};
    }
  }
  return out;
}
