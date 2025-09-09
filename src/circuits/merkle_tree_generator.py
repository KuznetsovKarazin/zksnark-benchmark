"""
Merkle tree generator for zkSNARK benchmarks.
Creates valid merkle proofs with proper sibling paths.
"""

from __future__ import annotations
import hashlib
import random
from typing import List, Dict, Any, Optional


class MerkleTree:
    """Simple Merkle tree implementation for proof generation."""
    
    def __init__(self, leaves: List[int], hash_func=None):
        self.leaves = leaves
        self.depth = self._calculate_depth(len(leaves))
        self.hash_func = hash_func or self._simple_hash
        self.tree = self._build_tree()
    
    def _calculate_depth(self, num_leaves: int) -> int:
        """Calculate tree depth for given number of leaves."""
        if num_leaves <= 1:
            return 1
        depth = 0
        size = 1
        while size < num_leaves:
            size *= 2
            depth += 1
        return depth
    
    def _simple_hash(self, left: int, right: int) -> int:
        """Simple hash function for demo purposes."""
        # Use a deterministic hash that fits field constraints
        combined = f"{left},{right}".encode()
        hash_val = int(hashlib.sha256(combined).hexdigest()[:15], 16)
        # Keep within reasonable field bounds
        return hash_val % (2**200)
    
    def _build_tree(self) -> List[List[int]]:
        """Build complete merkle tree bottom-up."""
        tree_size = 1 << self.depth
        
        # Initialize bottom level with leaves
        current_level = self.leaves[:]
        
        # Pad with zeros if needed
        while len(current_level) < tree_size:
            current_level.append(0)
        
        tree = [current_level[:]]
        
        # Build tree level by level
        for level in range(self.depth):
            next_level = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i + 1] if i + 1 < len(current_level) else 0
                parent = self.hash_func(left, right)
                next_level.append(parent)
            
            tree.append(next_level[:])
            current_level = next_level
            
            if len(current_level) == 1:
                break
        
        return tree
    
    def get_root(self) -> int:
        """Get merkle root."""
        return self.tree[-1][0]
    
    def get_proof(self, leaf_index: int) -> Dict[str, Any]:
        """Generate merkle proof for leaf at given index."""
        if leaf_index >= len(self.leaves):
            raise ValueError(f"Leaf index {leaf_index} out of bounds")
        
        path_elements = []
        path_indices = []
        
        current_index = leaf_index
        
        # Traverse from leaf to root
        for level in range(len(self.tree) - 1):
            level_size = len(self.tree[level])
            
            # Find sibling
            if current_index % 2 == 0:
                # Left child, sibling is right
                sibling_index = current_index + 1
                path_index = 0  # current node is left
            else:
                # Right child, sibling is left  
                sibling_index = current_index - 1
                path_index = 1  # current node is right
            
            # Get sibling value
            if sibling_index < level_size:
                sibling = self.tree[level][sibling_index]
            else:
                sibling = 0
            
            path_elements.append(sibling)
            path_indices.append(path_index)
            
            # Move to parent level
            current_index = current_index // 2
        
        return {
            "leaf": self.leaves[leaf_index],
            "pathElements": path_elements,
            "pathIndex": path_indices,  # Note: singular as expected by circuit
            "root": self.get_root()
        }


class PoseidonMerkleTree(MerkleTree):
    """Merkle tree using Poseidon hash approximation."""
    
    def __init__(self, leaves: List[int]):
        super().__init__(leaves, self._poseidon_like_hash)
    
    def _poseidon_like_hash(self, left: int, right: int) -> int:
        """Simplified Poseidon-like hash for testing."""
        # This is NOT real Poseidon, just a deterministic function
        # For real circuits, use actual Poseidon implementation
        x = (left + right) % (2**254)
        x = (x * 7 + 1) % (2**254)
        x = (x * x + left) % (2**254) 
        x = (x * 3 + right) % (2**254)
        return x


def generate_merkle_inputs(depth: int = 16, leaf_index: int = 0, seed: Optional[int] = None) -> Dict[str, Any]:
    """Generate valid merkle proof inputs for circuit."""
    if seed is not None:
        random.seed(seed)
    
    # Generate tree with 2^depth leaves
    num_leaves = 1 << depth
    leaves = [random.randint(1, 2**200) for _ in range(num_leaves)]
    
    # Ensure we have a specific leaf at desired index
    if leaf_index >= num_leaves:
        leaf_index = leaf_index % num_leaves
    
    # Build tree and get proof
    tree = PoseidonMerkleTree(leaves)
    proof = tree.get_proof(leaf_index)
    
    # Convert to string format expected by circuit
    return {
        "leaf": str(proof["leaf"]),
        "pathElements": [str(x) for x in proof["pathElements"]],
        "pathIndex": proof["pathIndex"],  # Keep as int array
        "root": str(proof["root"])
    }


# Test function to verify proof correctness
def verify_proof_locally(proof: Dict[str, Any]) -> bool:
    """Verify proof using same logic as circuit."""
    leaf = int(proof["leaf"])
    path_elements = [int(x) for x in proof["pathElements"]]
    path_indices = proof["pathIndex"] 
    expected_root = int(proof["root"])
    
    current = leaf
    
    for i, (sibling, direction) in enumerate(zip(path_elements, path_indices)):
        if direction == 0:
            # Current is left child
            left, right = current, sibling
        else:
            # Current is right child  
            left, right = sibling, current
        
        # Apply same hash as PoseidonMerkleTree
        x = (left + right) % (2**254)
        x = (x * 7 + 1) % (2**254)
        x = (x * x + left) % (2**254)
        x = (x * 3 + right) % (2**254)
        current = x
    
    return current == expected_root