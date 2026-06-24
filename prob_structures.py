"""
Probabilistic Data Structures
- Count-Min Sketch  (frequency estimation)
- HyperLogLog       (cardinality / distinct count)
- Bloom Filter      (membership testing)
"""

import mmh3
import math
import array
from datasketch import HyperLogLog
from pybloom_live import BloomFilter


# ─────────────────────────────────────────────
# 1. Count-Min Sketch
# ─────────────────────────────────────────────
class CountMinSketch:
    """
    Estimates frequency of elements with error ±ε·N with probability 1-δ.
    depth = ceil(log(1/δ)), width = ceil(e/ε)
    """
    def __init__(self, epsilon=0.01, delta=0.01, width=10000, depth=10):  # Increased from 5000/8
        self.width  = math.ceil(math.e / epsilon)
        self.depth  = math.ceil(math.log(1 / delta))
        self.table  = [[0] * width for _ in range(depth)]
        self.seeds  = list(range(self.depth))

    def add(self, item):
        for i, seed in enumerate(self.seeds):
            col = mmh3.hash(str(item), seed) % self.width
            self.table[i][col] += 1

    def query(self, item):
        return min(
            self.table[i][mmh3.hash(str(item), seed) % self.width]
            for i, seed in enumerate(self.seeds)
        )

    def reset(self):
        self.table = [[0] * self.width for _ in range(self.depth)]


# ─────────────────────────────────────────────
# 2. HyperLogLog  (wraps datasketch)
# ─────────────────────────────────────────────
class HLLCounter:
    """Estimates distinct element count. ~2% std error with p=12."""
    def __init__(self, p=12):
        self.hll = HyperLogLog(p=p)

    def add(self, item):
        self.hll.update(str(item).encode())

    def count(self):
        return int(self.hll.count())

    def reset(self):
        self.hll = HyperLogLog(p=12)


# ─────────────────────────────────────────────
# 3. Bloom Filter  (wraps pybloom_live)
# ─────────────────────────────────────────────
class BloomMembership:
    """
    Answers 'is X in the set?' with no false negatives.
    false_positive_rate controls accuracy vs memory trade-off.
    """
    def __init__(self, capacity=100_000, false_positive_rate=0.01):
        self.bf = BloomFilter(capacity=capacity,
                              error_rate=false_positive_rate)
        self.capacity = capacity
        self.fpr = false_positive_rate

    def add(self, item):
        self.bf.add(str(item))

    def contains(self, item):
        return str(item) in self.bf

    def reset(self):
        self.bf = BloomFilter(capacity=self.capacity,
                              error_rate=self.fpr)
