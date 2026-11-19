"""Bind archived Groth16 proofs to the exact static PolicyGate calldata.

This is an evidence consistency check, not cryptographic verification. The
separate snarkjs verifier checks the proof equations. All depositZK calls,
including deliberately rejected calls, must contain a saved proof. Failed
calls may intentionally use a different action amount or nonce.
"""

# keccak256("depositZK((uint256[2],uint256[2][2],uint256[2],uint256[8]),uint256,uint256)")[:4]
DEPOSIT_ZK_SELECTOR = 'fbd5c872'
AMOUNT = 100 * 10**18


def proof_words(entry):
    proof, signals = entry['proof'], entry['publicSignals']
    assert proof['protocol'] == 'groth16' and proof['curve'] == 'bn128'
    assert len(proof['pi_a']) == len(proof['pi_c']) == 3
    assert len(proof['pi_b']) == 3 and all(len(row) == 2 for row in proof['pi_b'])
    assert [int(v) for v in proof['pi_a'][2:]] == [1]
    assert [int(v) for v in proof['pi_c'][2:]] == [1]
    assert [int(v) for v in proof['pi_b'][2]] == [1, 0]
    assert len(signals) == 8
    # snarkjs uses the opposite Fq2 coordinate order from the Solidity ABI.
    values = [*proof['pi_a'][:2], *reversed(proof['pi_b'][0]),
              *reversed(proof['pi_b'][1]), *proof['pi_c'][:2], *signals]
    words = tuple(int(v) for v in values)
    assert all(0 <= v < 2**256 for v in words)
    return words


def check_proof_binding(raw):
    proofs = raw['proofs']
    by_payload = {}
    for index, proof in enumerate(proofs):
        assert proof['index'] == index, 'non-contiguous proof indices'
        key = (proof['scenario'], proof_words(proof))
        assert key not in by_payload, 'duplicate archived proof payload'
        by_payload[key] = index
    used, calls = set(), 0
    for tx in raw['transactions']:
        data = bytes.fromhex(tx['transaction']['data'].removeprefix('0x'))
        linked = tx.get('proof_index')
        if data[:4].hex() != DEPOSIT_ZK_SELECTOR:
            assert linked is None, 'proof link on non-depositZK transaction'
            continue
        assert len(data) == 4 + 18 * 32, 'unexpected depositZK ABI size'
        words = tuple(int.from_bytes(data[i:i + 32], 'big') for i in range(4, len(data), 32))
        key = (tx['scenario'], words[:16])
        assert key in by_payload, 'transaction calldata has no matching archived proof'
        index = by_payload[key]
        if linked is not None:
            assert linked == index, 'proof index differs from transaction calldata'
        if tx['receipt']['status'] == 1:
            assert tx['category'] in ('access', 'diagnostic_access')
            assert words[16:] == (AMOUNT, int(proofs[index]['nonce'])), 'wrong successful action arguments'
            assert tx['timestamp'] == int(proofs[index]['t']), 'proof/transaction time mismatch'
        used.add(index)
        calls += 1
    assert used == set(range(len(proofs))), 'archived proof is not present in any transaction'
    return {'proofs_bound': len(used), 'zk_calls_bound': calls}
