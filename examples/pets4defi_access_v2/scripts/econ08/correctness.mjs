import assert from 'node:assert/strict';
import {ethers} from 'ethers';
import * as snarkjs from 'snarkjs';
import {makeFixtures} from '../fixtures.mjs';
import {context, AMOUNT} from './harness.mjs';
import {MECHANISMS, DELTAS, DAY, TTL, HORIZON} from './config.mjs';

export async function correctness(env, data, checkpoint=()=>{}) {
  // Every native mechanism and delta: own revocation, exact boundary, and
  // repeated publication must not extend the first invalidation deadline.
  for(const mechanism of MECHANISMS) for(const delta of DELTAS) {
    const c=await context(env,data,{...mechanism,delta,id:`check_${mechanism.name}_d${delta}`,purpose:'correctness'});
    try {
      await c.deposit(c.base,{expectedEvent:'first'});
      const t=c.base+BigInt(DAY), deadline=t+BigInt(delta);
      await c.deposit(t-1n,{expectedEvent:'hit'});
      const oldProof=mechanism.family==='zk'?await c.proof(t):null;
      const oldEpoch=await c.registry.securityEpoch();
      await c.revoke(0,0,t,{own:true});
      if(oldProof) await c.reject('old_root_presentation_immediate','depositZK',
        [oldProof.tuple,AMOUNT,oldProof.nonce],t,'InvalidPublicSignals');
      if(delta>0) {
        await c.revoke(0,1,t+1n);
        const answer=await c.registry.securityDeadline(oldEpoch,delta);
        assert.equal(answer[1],deadline);
        c.check('second_update_preserves_first_deadline',{deadline,method:'view'});
        await c.deposit(deadline-1n,{expectedEvent:'hit'});
        c.check('own_revoked_cache_allowed_at_deadline_minus_one',{at:deadline-1n,method:'transaction'});
      }
      const reason=mechanism.family==='zk'?'StaleAuthorization':'CredentialRevoked';
      await c.reject('own_revoked_at_deadline','depositCached',[AMOUNT,await c.gate.nonces(c.wallet)],deadline,reason);
      await c.reject('own_revoked_after_deadline','depositCached',[AMOUNT,await c.gate.nonces(c.wallet)],deadline+1n,reason);
      if(mechanism.family==='signed') await c.reject('own_revoked_full_signed_at_deadline','depositSigned',
        [c.credential,c.signature,AMOUNT,await c.gate.nonces(c.wallet)],deadline+1n,'CredentialRevoked');
      c.check('own_revocation_case_complete',{family:mechanism.family,groups:mechanism.groups,delta});
    } finally {await c.connection.close();}
    checkpoint(); console.log(`PASS ${c.id}`);
  }
  // Emergency changes override even the largest permitted ordinary delay.
  for(const mechanism of MECHANISMS) for(const emergency of ['policy','disable']) {
    const c=await context(env,data,{...mechanism,delta:DAY,id:`check_${mechanism.name}_${emergency}`,purpose:'correctness'});
    try {
      await c.deposit(c.base,{expectedEvent:'first'});
      const t=c.base+1n;await c.advance(t);await c.pin(t);
      const tx=emergency==='policy'?await c.registry.updatePolicy(c.fixture.policyRoot,3,TTL):await c.registry.disableIssuer(0);
      await c.receipt(tx,'emergency_update','operator',{emergency});
      const reason=mechanism.family==='zk'?'StaleAuthorization':emergency==='policy'?'WrongPolicyVersion':'InactiveIssuer';
      await c.reject(`${emergency}_immediate`,'depositCached',[AMOUNT,1],t,reason);
    } finally {await c.connection.close();}
    checkpoint();console.log(`PASS ${c.id}`);
  }
  const c=await context(env,data,{id:'check_bindings_and_expiry',family:'zk',groups:2,delta:DAY,purpose:'correctness'});
  try {
    const t=c.base,pr=await c.proof(t);
    await c.reject('wrong_wallet','depositZK',[pr.tuple,AMOUNT,0],t,'InvalidPublicSignals',
      {g:c.gate.connect(c.signers[6]),w:c.addresses[6]});
    await c.reject('wrong_amount','depositZK',[pr.tuple,AMOUNT+1n,0],t,'InvalidPublicSignals');
    await c.reject('wrong_nonce','depositZK',[pr.tuple,AMOUNT,1],t,'InvalidNonce');
    const wrongChainScope=BigInt(ethers.keccak256(ethers.AbiCoder.defaultAbiCoder().encode(
      ['uint256','address','uint256'],[31338,c.gate.target,1])))%await c.gate.SNARK_FIELD();
    const wrongChain=await c.proof(t,{inputOverrides:{scope:wrongChainScope}});
    await c.reject('wrong_chain','depositZK',[wrongChain.tuple,AMOUNT,0],t,'InvalidPublicSignals');
    const wrongContract=await c.proof(t,{inputOverrides:{scope:await c.gates[1].computeScope()}});
    await c.reject('wrong_contract','depositZK',[wrongContract.tuple,AMOUNT,0],t,'InvalidPublicSignals');
    const otherGroup=await c.proof(t,{g:c.gates[1],f:c.fixtures[1],issuerIndex:2});
    await c.reject('cross_group_proof','depositZK',[otherGroup.tuple,AMOUNT,0],t,'InvalidPublicSignals');
    await c.pin(t);await c.receipt(await c.gate.depositZK(pr.tuple,AMOUNT,0),'diagnostic_access','holder');
    await c.reject('replay','depositZK',[pr.tuple,AMOUNT,0],t,'InvalidNonce');
    await c.deposit(t+BigInt(TTL)-1n,{expectedEvent:'hit'});
    await c.reject('ttl_exact','depositCached',[AMOUNT,2],t+BigInt(TTL),'AuthorizationExpired');
    // Fresh proof prepared for the current nonce: only root freshness changes.
    const t2=t+BigInt(TTL)+1n,old=await c.proof(t2);
    await c.revoke(1,1,t2);
    await c.reject('stale_root_only','depositZK',[old.tuple,AMOUNT,old.nonce],t2,'InvalidPublicSignals');
    // Unaffected holder can obtain a new proof immediately after publication.
    await c.deposit(t2,{expectedEvent:'reauthorize'});
    c.check('unaffected_holder_new_proof_accepted',{method:'transaction'});
    await c.deposit(t+BigInt(HORIZON)-1n,{expectedEvent:'reauthorize'});
    await c.reject('credential_expiry_exact','depositCached',[AMOUNT,4],t+BigInt(HORIZON),'AuthorizationExpired');
    for(const [name,patch] of [
      ['low_tier',{tier:1n}],['forbidden_jurisdiction',{jurisdiction:999n}],
      ['expired_credential',{credentialExpiry:t}],['not_yet_valid',{notBefore:t+1n}],
    ]) {
      const f=await makeFixtures(c.addresses.slice(0,4),t);f.setCredential(0,0,patch);
      const input=f.inputFor({scope:1n,requestHash:1n,windowStart:t,windowEnd:t+BigInt(TTL)});
      await assert.rejects(snarkjs.groth16.fullProve(input,'build/access_js/access.wasm','build/access_final.zkey',undefined,undefined,{singleThread:true}),
        e=>/Assert Failed|Error in template/.test(e.message),name);
      c.check(name,{method:'witness_constraints',input});
    }
    const f=c.fixture;
    const removed=f.removeCredential(0,0);
    assert(removed>0n);
    const input=f.inputFor({scope:1n,requestHash:1n,windowStart:t,windowEnd:t+BigInt(TTL)});
    await assert.rejects(snarkjs.groth16.fullProve(input,'build/access_js/access.wasm','build/access_final.zkey',undefined,undefined,{singleThread:true}),
      e=>/Assert Failed|Error in template/.test(e.message));
    c.check('revoked_leaf_cannot_produce_new_membership_proof',{method:'witness_constraints',input});
  } finally {await c.connection.close();}
  checkpoint();console.log('PASS bindings, replay, expiry and predicate checks');
}
