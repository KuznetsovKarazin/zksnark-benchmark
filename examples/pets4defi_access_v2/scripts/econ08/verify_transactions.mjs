import assert from 'node:assert/strict';
import {Transaction} from 'ethers';

// Reconstruct the signed transaction, so matching JSON hash fields alone cannot
// conceal changed calldata. This verifies archived evidence, not chain finality.
export function verifyTransactions(transactions) {
  for (const entry of transactions) {
    const tx = Transaction.from(entry.transaction);
    assert.equal(tx.hash, entry.transaction.hash, 'signed transaction hash mismatch');
    assert.equal(tx.hash, entry.receipt.hash, 'transaction/receipt hash mismatch');
    assert.equal(tx.from, entry.receipt.from, 'transaction/receipt sender mismatch');
    assert.equal(tx.to, entry.receipt.to, 'transaction/receipt destination mismatch');
  }
  return transactions.length;
}
