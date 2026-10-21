pragma circom 2.2.3;
include "circomlib/circuits/poseidon.circom";
include "circomlib/circuits/comparators.circom";
include "circomlib/circuits/bitify.circom";

template Membership(depth) {
    signal input leaf;
    signal input siblings[depth];
    signal input directions[depth];
    signal output root;
    signal nodes[depth+1];
    signal left[depth];
    signal right[depth];
    component hashes[depth];
    nodes[0] <== leaf;
    for (var i=0;i<depth;i++) {
        directions[i]*(directions[i]-1) === 0;
        left[i] <== nodes[i] + directions[i]*(siblings[i]-nodes[i]);
        right[i] <== siblings[i] + directions[i]*(nodes[i]-siblings[i]);
        hashes[i] = Poseidon(2);
        hashes[i].inputs[0] <== left[i];
        hashes[i].inputs[1] <== right[i];
        nodes[i+1] <== hashes[i].out;
    }
    root <== nodes[depth];
}

// Hierarchy: private credential -> private issuer root -> public issuer registry.
// Current active-root membership is the status mechanism; root authentication
// and current-root enforcement are the registry/gate's responsibilities.
template Access(credentialDepth,issuerDepth,policyDepth) {
    signal input secret;
    signal input salt;
    signal input issuerId;
    signal input tier;
    signal input jurisdiction;
    signal input notBefore;
    signal input credentialExpiry;
    signal input credentialSiblings[credentialDepth];
    signal input credentialDirections[credentialDepth];
    signal input issuerSiblings[issuerDepth];
    signal input issuerDirections[issuerDepth];
    signal input policySiblings[policyDepth];
    signal input policyDirections[policyDepth];

    signal input registryRoot;
    signal input policyRoot;
    signal input minTier;
    signal input windowStart;
    signal input windowEnd;
    signal input scope;
    signal input requestHash;
    signal output scopeNullifier;

    component boundedTier=Num2Bits(8); boundedTier.in <== tier;
    component boundedMinimum=Num2Bits(8); boundedMinimum.in <== minTier;
    component boundedJurisdiction=Num2Bits(16); boundedJurisdiction.in <== jurisdiction;
    component boundedIssuer=Num2Bits(160); boundedIssuer.in <== issuerId;
    component date0=Num2Bits(64); date0.in <== notBefore;
    component date1=Num2Bits(64); date1.in <== credentialExpiry;
    component date2=Num2Bits(64); date2.in <== windowStart;
    component date3=Num2Bits(64); date3.in <== windowEnd;
    // Explicitly consume the public context without an extra public hash output.
    // The gate uses the low 248 bits of Keccak; changing context must fail verify.
    component boundedRequest=Num2Bits(248); boundedRequest.in <== requestHash;
    component enough=LessEqThan(8); enough.in[0]<==minTier; enough.in[1]<==tier; enough.out===1;
    component begins=LessEqThan(64); begins.in[0]<==notBefore; begins.in[1]<==windowStart; begins.out===1;
    component ordered=LessThan(64); ordered.in[0]<==windowStart; ordered.in[1]<==windowEnd; ordered.out===1;
    component ends=LessEqThan(64); ends.in[0]<==windowEnd; ends.in[1]<==credentialExpiry; ends.out===1;

    component holder=Poseidon(2); holder.inputs[0]<==11; holder.inputs[1]<==secret;
    component attrs=Poseidon(2); attrs.inputs[0]<==tier; attrs.inputs[1]<==jurisdiction;
    component dates=Poseidon(2); dates.inputs[0]<==notBefore; dates.inputs[1]<==credentialExpiry;
    component ds=Poseidon(2); ds.inputs[0]<==dates.out; ds.inputs[1]<==salt;
    component ads=Poseidon(2); ads.inputs[0]<==attrs.out; ads.inputs[1]<==ds.out;
    component issued=Poseidon(2); issued.inputs[0]<==issuerId; issued.inputs[1]<==ads.out;
    component taggedHolder=Poseidon(2); taggedHolder.inputs[0]<==12; taggedHolder.inputs[1]<==holder.out;
    component leaf=Poseidon(2); leaf.inputs[0]<==taggedHolder.out; leaf.inputs[1]<==issued.out;
    component credentials=Membership(credentialDepth);
    credentials.leaf<==leaf.out;
    for(var i=0;i<credentialDepth;i++){credentials.siblings[i]<==credentialSiblings[i];credentials.directions[i]<==credentialDirections[i];}

    component issuerTag=Poseidon(2); issuerTag.inputs[0]<==21; issuerTag.inputs[1]<==issuerId;
    component issuerLeaf=Poseidon(2); issuerLeaf.inputs[0]<==issuerTag.out; issuerLeaf.inputs[1]<==credentials.root;
    component issuers=Membership(issuerDepth); issuers.leaf<==issuerLeaf.out;
    for(var i=0;i<issuerDepth;i++){issuers.siblings[i]<==issuerSiblings[i];issuers.directions[i]<==issuerDirections[i];}
    issuers.root===registryRoot;

    component jurisdictionLeaf=Poseidon(2); jurisdictionLeaf.inputs[0]<==31; jurisdictionLeaf.inputs[1]<==jurisdiction;
    component policy=Membership(policyDepth); policy.leaf<==jurisdictionLeaf.out;
    for(var i=0;i<policyDepth;i++){policy.siblings[i]<==policySiblings[i];policy.directions[i]<==policyDirections[i];}
    policy.root===policyRoot;

    // Stable within one application scope; sequential action nonces prevent replay.
    // This is a pseudonym, not a one-use-per-scope voting nullifier.
    component pseudonym=Poseidon(2); pseudonym.inputs[0]<==secret; pseudonym.inputs[1]<==scope;
    scopeNullifier<==pseudonym.out;
}

component main {public [registryRoot,policyRoot,minTier,windowStart,windowEnd,scope,requestHash]} = Access(10,2,3);
