"""Evidence-corruption regression checks, not a copy of the implementation."""
import gzip
import hashlib
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
spec = importlib.util.spec_from_file_location('econ08_checker', HERE / 'check.py')
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class EvidenceIntegrity(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name) / 'evidence'
        shutil.copytree(ROOT / 'results/econ08_native_pilot', self.folder)

    def tearDown(self):
        self.temp.cleanup()

    def replace(self, name, value, compressed=False):
        contents = (json.dumps(value, indent=2) + '\n').encode()
        (self.folder / name).write_bytes(gzip.compress(contents) if compressed else contents)
        # Rehash deliberately: semantic consistency must still detect corruption.
        manifest = json.loads((self.folder / 'manifest.json').read_text())
        manifest[name] = hashlib.sha256((self.folder / name).read_bytes()).hexdigest()
        (self.folder / 'manifest.json').write_text(json.dumps(manifest))

    def test_original_evidence_passes(self):
        self.assertEqual(checker.check(self.folder)['workload_accesses'], 1616)

    def test_double_counted_setup_is_rejected(self):
        report = json.loads((self.folder / 'report.json').read_text())
        report['summaries'][0]['operator_setup_gas'] *= 2
        self.replace('report.json', report)
        with self.assertRaises(AssertionError):
            checker.check(self.folder)

    def test_dropped_low_workload_publication_is_rejected(self):
        name = 'receipts_and_proofs.json.gz'
        raw = json.loads(gzip.decompress((self.folder / name).read_bytes()))
        index = next(i for i, t in enumerate(raw['transactions'])
                     if t['scenario'] == 'zk_B1_d0_LOW' and t['category'] == 'status_publication')
        raw['transactions'].pop(index)
        self.replace(name, raw, compressed=True)
        with self.assertRaises(AssertionError):
            checker.check(self.folder)

    def test_false_cache_hit_is_rejected(self):
        name = 'accesses.json'
        rows = json.loads((self.folder / name).read_text())
        row = next(a for a in rows if a['scenario'] == 'zk_B1_d0_HIGH' and a['event'] == 'reauthorize')
        row['event'] = 'hit'
        self.replace(name, rows)
        with self.assertRaises(AssertionError):
            checker.check(self.folder)

    def test_mutated_rejection_state_is_rejected(self):
        report = json.loads((self.folder / 'report.json').read_text())
        row = next(c for c in report['checks'] if 'before' in c)
        row['after']['nonce'] = str(int(row['after']['nonce']) + 1)
        self.replace('report.json', report)
        with self.assertRaises(AssertionError):
            checker.check(self.folder)

    def corrupt_raw(self, change):
        name = 'receipts_and_proofs.json.gz'
        raw = json.loads(gzip.decompress((self.folder / name).read_bytes()))
        change(raw)
        self.replace(name, raw, compressed=True)
        with self.assertRaises(AssertionError):
            checker.check(self.folder)

    def test_proof_coordinate_not_in_transaction_is_rejected(self):
        def change(raw):
            proof = raw['proofs'][0]['proof']
            proof['pi_a'][0] = str(int(proof['pi_a'][0]) + 1)
        self.corrupt_raw(change)

    def test_public_input_not_in_transaction_is_rejected(self):
        def change(raw):
            signals = raw['proofs'][0]['publicSignals']
            signals[7] = str(int(signals[7]) + 1)
        self.corrupt_raw(change)

    def test_calldata_proof_mutation_is_rejected(self):
        def change(raw):
            tx = next(t for t in raw['transactions'] if t.get('proof_index') == 0)
            data = tx['transaction']['data']
            # Change the first proof coordinate, retaining calldata size and hash metadata.
            word = int(data[10:74], 16) + 1
            tx['transaction']['data'] = data[:10] + f'{word:064x}' + data[74:]
        self.corrupt_raw(change)

    def test_proof_link_to_different_saved_proof_is_rejected(self):
        def change(raw):
            tx = next(t for t in raw['transactions'] if t.get('proof_index') == 0)
            tx['proof_index'] = 1
        self.corrupt_raw(change)

    def test_changed_zk_selector_is_rejected(self):
        def change(raw):
            tx = next(t for t in raw['transactions'] if t.get('proof_index') == 0)
            tx['transaction']['data'] = '0x00000000' + tx['transaction']['data'][10:]
        self.corrupt_raw(change)


if __name__ == '__main__':
    unittest.main()
