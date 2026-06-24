"""
E-Commerce Adaptive Load-Shedding Pipeline
===========================================
Simulates a flash-sale traffic spike on an e-commerce platform.

Questions answered by Probabilistic Data Structures:
  ① Count-Min Sketch  → "Which product is viewed / ordered most?"
  ② HyperLogLog       → "How many unique users / products were active?"
  ③ Bloom Filter      → "Has user X already ordered product Y?" (dedup)

Normal mode  : exact Python dicts / sets  (reported when load is low)
Adaptive mode: probabilistic answers reported (when queue overloads)

SHADOW MODE: Both exact AND probabilistic run on EVERY event.
  Mode only controls which answer is served to the query layer.
  This enables true apples-to-apples deviation measurement.
"""

import csv
import queue
import random
import threading
import time
from collections import defaultdict
from os import path
from pathlib import Path

from ecommerce_data  import generate_event, event_key, PRODUCTS, USERS
from load_monitor    import LoadMonitor, SmartValve
from prob_structures import BloomMembership, CountMinSketch, HLLCounter

# ── Config ────────────────────────────────────────────────────────────────
QUEUE_CAPACITY  = 2000
HIGH_THRESHOLD  = 300
LOW_THRESHOLD   = 100
NORMAL_RATE     = 500    # events/sec — steady traffic
SPIKE_RATE      = 4000   # events/sec — flash sale surge
SPIKE_AT        = 6      # seconds into run
SPIKE_DURATION  = 10     # seconds spike lasts
CONSUMER_RATE   = 600    # intentionally slower → queue fills → mode switch
TOTAL_RUNTIME   = 40


# ── Exact store (Normal mode) ─────────────────────────────────────────────
class ExactStore:
    """Ground-truth counters used in NORMAL mode."""
    def __init__(self):
        # Frequency maps keyed by event_type → product_id
        self.product_views  = defaultdict(int)
        self.product_orders = defaultdict(int)
        self.product_cart   = defaultdict(int)
        self.category_views = defaultdict(int)
        # Unique sets
        self.unique_users    = set()
        self.unique_products = set()
        # Membership: "user already ordered product"
        self.user_orders     = set()   # elements: "user_id::product_id"

    def add(self, event):
        pid  = event["product_id"]
        uid  = event["user_id"]
        cat  = event["category"]
        et   = event["type"]

        self.unique_users.add(uid)
        self.unique_products.add(pid)

        if et == "PRODUCT_VIEW":
            self.product_views[pid]  += 1
            self.category_views[cat] += 1
        elif et == "ORDER_PLACED":
            self.product_orders[pid] += 1
            self.user_orders.add(f"{uid}::{pid}")
        elif et == "ADD_TO_CART":
            self.product_cart[pid]   += 1

    # ── Queries ────────────────────────────────────────────────────────────
    def top_viewed(self, n=5):
        return sorted(self.product_views.items(), key=lambda x: -x[1])[:n]

    def top_ordered(self, n=5):
        return sorted(self.product_orders.items(), key=lambda x: -x[1])[:n]

    def top_category(self, n=3):
        return sorted(self.category_views.items(), key=lambda x: -x[1])[:n]

    def has_ordered(self, uid, pid):
        return f"{uid}::{pid}" in self.user_orders


# ── Stats ─────────────────────────────────────────────────────────────────
class Stats:
    def __init__(self):
        self.lock              = threading.Lock()
        self.produced          = 0
        self.consumed_normal   = 0
        self.consumed_adaptive = 0
        self.dropped           = 0
        self.snapshots         = []

    def snap(self, t, mode, qsize, norm, adap, drop):
        with self.lock:
            self.snapshots.append(dict(t=t, mode=mode, q_size=qsize,
                                       normal=norm, adaptive=adap, dropped=drop))

STATS = Stats()


# ── Producer ──────────────────────────────────────────────────────────────
def producer(q, stop_event, start_time):
    while not stop_event.is_set():
        elapsed = time.time() - start_time
        spike   = SPIKE_AT <= elapsed < SPIKE_AT + SPIKE_DURATION
        rate    = SPIKE_RATE if spike else NORMAL_RATE
        event   = generate_event(spike=spike)
        try:
            q.put_nowait(event)
            with STATS.lock: STATS.produced += 1
        except queue.Full:
            with STATS.lock: STATS.dropped  += 1
        time.sleep(1.0 / rate)


# ── Consumer ──────────────────────────────────────────────────────────────
def consumer(q, valve, exact,
             cm_views, cm_orders, cm_cart,     # 3 CM sketches (one per event type)
             hll_users, hll_products,           # 2 HLLs
             bloom_user_orders,                 # 1 Bloom
             stop_event, start_time):

    interval       = 1.0 / CONSUMER_RATE
    last_snap      = time.time()
    snap_interval  = 1.0

    while not stop_event.is_set():
        try:
            event = q.get(timeout=0.05)
        except queue.Empty:
            continue

        mode = valve.current_mode()
        pid  = event["product_id"]
        uid  = event["user_id"]
        et   = event["type"]

        # ── SHADOW MODE: both exact and probabilistic run on every event ──
        # Exact store — always updated (ground truth for comparison)
        exact.add(event)

        # Probabilistic structures — always updated (for fair comparison)
        if et == "PRODUCT_VIEW":
            cm_views.add(pid)
        elif et == "ORDER_PLACED":
            cm_orders.add(pid)
            bloom_user_orders.add(f"{uid}::{pid}")
        elif et == "ADD_TO_CART":
            cm_cart.add(pid)
        hll_users.add(uid)
        hll_products.add(pid)

        # Mode only controls which answer is REPORTED (not what is computed)
        with STATS.lock:
            if mode == SmartValve.NORMAL:
                STATS.consumed_normal   += 1
            else:
                STATS.consumed_adaptive += 1
        # ─────────────────────────────────────────────────────────────────

        now = time.time()
        if now - last_snap >= snap_interval:
            with STATS.lock:
                n, a, d = STATS.consumed_normal, STATS.consumed_adaptive, STATS.dropped
            STATS.snap(now - start_time, mode, q.qsize(), n, a, d)
            last_snap = now

        time.sleep(interval)


# ── Query Comparison ──────────────────────────────────────────────────────
def run_query_comparison(exact,
                          cm_views, cm_orders, cm_cart,
                          hll_users, hll_products,
                          bloom_user_orders):

    # Build a name lookup
    name = {p[0]: p[1] for p in PRODUCTS}  # p[0] = id, p[1] = name

    print("\n" + "═"*65)
    print("  E-COMMERCE QUERY RESULTS: Exact vs Probabilistic")
    print("  (Shadow mode — both processed same stream — true deviation)")
    print("═"*65)

    # ── Q1: Top viewed products ──────────────────────────────────────────
    print("\n① Most-Viewed Products  [Count-Min Sketch vs Exact]")
    top5 = exact.top_viewed(5)
    print(f"  {'Product':<22} {'Name':<20} {'Exact':>7} {'CM-Sketch':>10} {'Err%':>7}")
    print(f"  {'-'*22} {'-'*20} {'-'*7} {'-'*10} {'-'*7}")
    for pid, ef in top5:
        af  = cm_views.query(pid)
        err = abs(af - ef) / max(ef, 1) * 100
        print(f"  {pid:<22} {name.get(pid,'?'):<20} {ef:>7} {af:>10} {err:>6.1f}%")

    # ── Q2: Most ordered products ────────────────────────────────────────
    print("\n② Most-Ordered Products  [Count-Min Sketch vs Exact]")
    top5o = exact.top_ordered(5)
    if top5o:
        print(f"  {'Product':<22} {'Name':<20} {'Exact':>7} {'CM-Sketch':>10} {'Err%':>7}")
        print(f"  {'-'*22} {'-'*20} {'-'*7} {'-'*10} {'-'*7}")
        for pid, ef in top5o:
            af  = cm_orders.query(pid)
            err = abs(af - ef) / max(ef, 1) * 100
            print(f"  {pid:<22} {name.get(pid,'?'):<20} {ef:>7} {af:>10} {err:>6.1f}%")
    else:
        print("  (no orders yet in NORMAL-mode window)")

    # ── Q3: Most added-to-cart ───────────────────────────────────────────
    print("\n③ Most Added-to-Cart  [Count-Min Sketch vs Exact]")
    top5c = sorted(exact.product_cart.items(), key=lambda x: -x[1])[:5]
    if top5c:
        print(f"  {'Product':<22} {'Name':<20} {'Exact':>7} {'CM-Sketch':>10} {'Err%':>7}")
        print(f"  {'-'*22} {'-'*20} {'-'*7} {'-'*10} {'-'*7}")
        for pid, ef in top5c:
            af  = cm_cart.query(pid)
            err = abs(af - ef) / max(ef, 1) * 100
            print(f"  {pid:<22} {name.get(pid,'?'):<20} {ef:>7} {af:>10} {err:>6.1f}%")
    else:
        print("  (no cart events in NORMAL-mode window)")

    # ── Q4: Unique active users & products ───────────────────────────────
    print("\n④ Unique Active Users & Products  [HyperLogLog vs Exact]")
    eu = len(exact.unique_users);    hu = hll_users.count()
    ep = len(exact.unique_products); hp = hll_products.count()
    eu_err = abs(hu - eu) / max(eu, 1) * 100
    ep_err = abs(hp - ep) / max(ep, 1) * 100
    print(f"  Unique Users    — Exact: {eu:>5}  HLL: {hu:>5}  Error: {eu_err:.1f}%")
    print(f"  Unique Products — Exact: {ep:>5}  HLL: {hp:>5}  Error: {ep_err:.1f}%")

    # ── Q5: "Has this user already ordered this product?" ────────────────
    print("\n⑤ Has User Already Ordered Product?  [Bloom Filter vs Exact]")
    # Pick random (user, product) pairs to test — same source of truth
    test_pairs = [(random.choice(USERS), random.choice(PRODUCTS)[0])
                  for _ in range(200)]
    tp = fp = tn = fn = 0
    for uid, pid in test_pairs:
        actual = exact.has_ordered(uid, pid)
        approx = bloom_user_orders.contains(f"{uid}::{pid}")
        if actual and approx:       tp += 1
        elif not actual and approx: fp += 1
        elif not actual:            tn += 1
        else:                       fn += 1
    total = tp + fp + tn + fn
    print(f"  Tested {total} random (user, product) pairs:")
    print(f"   True Positive  : {tp:>4}  (correctly said 'yes, ordered')")
    print(f"   False Positive : {fp:>4}  (said 'ordered' but wasn't — acceptable)")
    print(f"   True Negative  : {tn:>4}  (correctly said 'not ordered')")
    print(f"   False Negative : {fn:>4}  (should be 0 — Bloom never misses real orders)")

    # ── Q6: Top categories ───────────────────────────────────────────────
    print("\n⑥ Top Categories by Views  [Exact — Normal mode only]")
    for cat, cnt in exact.top_category(5):
        print(f"  {cat:<15} {cnt:>6} views")

    # ── Deviation Summary ─────────────────────────────────────────────────
    print("\n" + "═"*65)
    print("  DEVIATION SUMMARY")
    print("═"*65)

    all_v = [(ef, cm_views.query(pid))  for pid, ef in exact.product_views.items()  if ef > 0]
    all_o = [(ef, cm_orders.query(pid)) for pid, ef in exact.product_orders.items() if ef > 0]
    all_c = [(ef, cm_cart.query(pid))   for pid, ef in exact.product_cart.items()   if ef > 0]

    for label, pairs in [("Views", all_v), ("Orders", all_o), ("Cart", all_c)]:
        if pairs:
            mape    = sum(abs(a - e) / e * 100 for e, a in pairs) / len(pairs)
            max_err = max(abs(a - e) / e * 100 for e, a in pairs)
            print(f"  CM Sketch {label:<8}: MAPE = {mape:5.2f}%   Max error = {max_err:5.2f}%")

    print(f"  HLL Users          : Error = {eu_err:.2f}%"
          f"  (theoretical bound = 1.62%)")
    print(f"  HLL Products       : Error = {ep_err:.2f}%")
    print(f"  Bloom False Neg    : {fn}  (guarantee: must always be 0)")
    fpr_obs = fp / max(fp + tn, 1) * 100
    print(f"  Bloom Observed FPR : {fpr_obs:.1f}%  (configured target: 1%)")

    
    print("\n  MAPE split by product frequency:")
    threshold = 50   # "heavy hitter" = seen more than 50 times
    heavy = [(ef, cm_views.query(pid)) for pid, ef in exact.product_views.items() if ef >= threshold]
    tail  = [(ef, cm_views.query(pid)) for pid, ef in exact.product_views.items() if ef < threshold]
    if heavy:
        mape_h = sum(abs(a-e)/e*100 for e,a in heavy)/len(heavy)
        print(f"  Heavy hitters (freq ≥ 50) : MAPE = {mape_h:.2f}%  ← what matters")
    if tail:
        mape_t = sum(abs(a-e)/e*100 for e,a in tail)/len(tail)
        print(f"  Tail items    (freq < 50) : MAPE = {mape_t:.2f}%  ← driven by rare items")


# ── Main ──────────────────────────────────────────────────────────────────
def main():
    print("=" * 65)
    print("  E-Commerce Adaptive Load-Shedding Pipeline  —  MTP")
    print("=" * 65)
    print(f"  Normal rate  : {NORMAL_RATE} ev/s")
    print(f"  Spike rate   : {SPIKE_RATE} ev/s  (flash sale at t={SPIKE_AT}s for {SPIKE_DURATION}s)")
    print(f"  Consumer rate: {CONSUMER_RATE} ev/s  (slower → queue fills → ADAPTIVE kicks in)")
    print(f"  Thresholds   : HIGH={HIGH_THRESHOLD}  LOW={LOW_THRESHOLD}")
    print(f"  Mode         : Shadow (exact + probabilistic run on every event)")
    print("=" * 65)

    q = queue.Queue(maxsize=QUEUE_CAPACITY)

    # Exact structures
    exact = ExactStore()

    # Probabilistic structures
    cm_views          = CountMinSketch(epsilon=0.005, delta=0.01)
    cm_orders         = CountMinSketch(epsilon=0.005, delta=0.01)
    cm_cart           = CountMinSketch(epsilon=0.005, delta=0.01)
    hll_users         = HLLCounter(p=12)
    hll_products      = HLLCounter(p=12)
    bloom_user_orders = BloomMembership(capacity=500_000, false_positive_rate=0.01)

    monitor = LoadMonitor(q, HIGH_THRESHOLD, LOW_THRESHOLD)
    valve   = SmartValve(monitor)
    monitor.start()

    stop_event = threading.Event()
    start_time = time.time()

    threads = [
        threading.Thread(target=producer,
                         args=(q, stop_event, start_time), daemon=True),
        threading.Thread(target=consumer,
                         args=(q, valve, exact,
                               cm_views, cm_orders, cm_cart,
                               hll_users, hll_products,
                               bloom_user_orders,
                               stop_event, start_time), daemon=True),
    ]
    for t in threads: t.start()

    try:
        while time.time() - start_time < TOTAL_RUNTIME:
            elapsed = time.time() - start_time
            mode    = valve.current_mode()
            spike   = "FLASH SALE" if SPIKE_AT <= elapsed < SPIKE_AT + SPIKE_DURATION else "          "
            with STATS.lock:
                prod = STATS.produced
                norm = STATS.consumed_normal
                adap = STATS.consumed_adaptive
                drop = STATS.dropped
            print(f"\r  t={elapsed:5.1f}s | {mode:<8} {spike} | Q={q.qsize():4d} | "
                  f"Norm={norm:6d} Adap={adap:6d} Drop={drop:5d}",
                  end="", flush=True)
            time.sleep(0.25)
    except KeyboardInterrupt:
        print("\n[Interrupted]")

    stop_event.set(); monitor.stop()

    print("\n\n" + "═"*65)
    print("  PIPELINE SUMMARY")
    print("═"*65)
    with STATS.lock:
        print(f"  Events produced    : {STATS.produced:>8}")
        print(f"  Normal processed   : {STATS.consumed_normal:>8}  (exact answers reported)")
        print(f"  Adaptive processed : {STATS.consumed_adaptive:>8}  (probabilistic answers reported)")
        print(f"  Dropped (overflow) : {STATS.dropped:>8}")

    run_query_comparison(exact,
                          cm_views, cm_orders, cm_cart,
                          hll_users, hll_products,
                          bloom_user_orders)

    # Save snapshots CSV
    output_dir = Path.home() / "Desktop" / "MTP" / "Project" / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)

    snapshot_file = output_dir / "ecom_snapshots.csv"
    with open(snapshot_file, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["t","mode","q_size","normal","adaptive","dropped"])
        w.writeheader(); w.writerows(STATS.snapshots)
    print(f"\n  Snapshots → {snapshot_file}")

if __name__ == "__main__":
    main()