import {buildPoseidon} from 'circomlibjs';

// Public, reproducible synthetic fixtures. Never use these secrets for real users.
export async function makeFixtures(issuerAddresses, now) {
  if (issuerAddresses.length !== 4) throw new Error('Exactly four issuer slots required');
  const poseidon = await buildPoseidon();
  const H = (a,b) => poseidon.F.toObject(poseidon([BigInt(a),BigInt(b)]));
  const notBefore=BigInt(now)-86400n, credentialExpiry=BigInt(now)+90n*86400n;
  const credentials=issuerAddresses.map((issuer,i)=>[0,1].map(j=>({
    secret:10001n+BigInt(i*100+j),salt:20001n+BigInt(i*100+j),
    issuerId:BigInt(issuer),tier:3n,jurisdiction:1n+BigInt(j),notBefore,credentialExpiry,
  })));
  const leaf=c=>H(H(12,H(11,c.secret)),H(c.issuerId,H(H(c.tier,c.jurisdiction),H(H(c.notBefore,c.credentialExpiry),c.salt))));
  class Tree {
    constructor(leaves,depth) {
      this.levels=[Array.from({length:2**depth},(_,i)=>leaves[i]??0n)];
      for(let d=0;d<depth;d++) {
        const row=this.levels[d];
        this.levels.push(Array.from({length:row.length/2},(_,i)=>H(row[i*2],row[i*2+1])));
      }
    }
    get root(){return this.levels.at(-1)[0];}
    path(index){
      const siblings=[],directions=[];
      for(let d=0;d<this.levels.length-1;d++) {
        siblings.push(this.levels[d][index^1]); directions.push(index&1); index>>=1;
      }
      return {siblings,directions};
    }
  }
  let trees=credentials.map(cs=>new Tree(cs.map(leaf),10));
  const disabled=[false,false,false,false], removed=credentials.map(()=>new Set());
  const policyCodes=[1,2,3,4,5,6,7,8],policy=new Tree(policyCodes.map(x=>H(31,x)),3);
  const registry=()=>new Tree(trees.map((tree,i)=>disabled[i]?0n:H(H(21,BigInt(issuerAddresses[i])),tree.root)),2);
  const rebuild=i=>{trees[i]=new Tree(credentials[i].map((c,j)=>removed[i].has(j)?0n:leaf(c)),10);return trees[i].root;};
  const stringify=x=>JSON.parse(JSON.stringify(x,(_,v)=>typeof v==='bigint'?v.toString():v));
  return {
    hash:H,credentials,policyCodes,policyRoot:policy.root,minTier:2n,maxTTL:30n*86400n,
    notBefore,credentialExpiry,
    get issuerRoots(){return trees.map(t=>t.root);},get registryRoot(){return registry().root;},
    refreshRoot(index,round){credentials[index][1].salt=50000n+BigInt(round);return rebuild(index);},
    setCredential(i,j,patch){Object.assign(credentials[i][j],patch);return rebuild(i);},
    removeCredential(i,j){removed[i].add(j);return rebuild(i);},
    setIssuerDisabled(index){disabled[index]=true;},
    inputFor({issuerIndex=0,credentialIndex=0,scope,requestHash,windowStart,windowEnd,...overrides}) {
      const c=credentials[issuerIndex][credentialIndex],cp=trees[issuerIndex].path(credentialIndex),ip=registry().path(issuerIndex);
      // For an intentionally forbidden-jurisdiction fixture, use an existing
      // path: the circuit must reject the leaf/root mismatch itself.
      const pi=Math.max(0,policyCodes.indexOf(Number(c.jurisdiction)));
      const pp=policy.path(pi);
      return stringify({...c,credentialSiblings:cp.siblings,credentialDirections:cp.directions,
        issuerSiblings:ip.siblings,issuerDirections:ip.directions,
        policySiblings:pp.siblings,policyDirections:pp.directions,
        registryRoot:registry().root,policyRoot:policy.root,minTier:2n,
        scope,requestHash,windowStart,windowEnd,...overrides});
    }
  };
}
