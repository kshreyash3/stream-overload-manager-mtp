"""
benchmark.py  —  E-Commerce edition
Generates 4 publication-ready charts:

"""

import os, csv, random, time
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from collections import defaultdict
from pathlib import Path

from ecommerce_data  import generate_event, event_key, PRODUCTS, USERS
from prob_structures import CountMinSketch, HLLCounter, BloomMembership

OUT = str(Path.home() / "Desktop" / "MTP" / "Project" / "outputs")

os.makedirs(OUT, exist_ok=True)

PALETTE = {
    "blue":   "#1565C0",
    "orange": "#E65100",
    "green":  "#2E7D32",
    "red":    "#C62828",
    "purple": "#6A1B9A",
    "teal":   "#00695C",
    "pink":   "#AD1457",
    "grey":   "#546E7A",
}


# ── 1. Pipeline Timeline ──────────────────────────────────────────────────
def timeline_chart():
    csv_path = f"{OUT}/ecom_snapshots.csv"
    if not os.path.exists(csv_path):
        print("  ⚠ Run pipeline.py first to generate ecom_snapshots.csv"); return

    rows = list(csv.DictReader(open(csv_path)))
    if not rows: return

    ts    = [float(r["t"])       for r in rows]
    qs    = [int(r["q_size"])    for r in rows]
    modes = [r["mode"]           for r in rows]
    norm  = [int(r["normal"])    for r in rows]
    adap  = [int(r["adaptive"])  for r in rows]
    drop  = [int(r["dropped"])   for r in rows]

    fig, axes = plt.subplots(3, 1, figsize=(13, 10), sharex=True)
    fig.suptitle("E-Commerce Flash Sale — Pipeline Behaviour", fontsize=14, fontweight="bold")

    # Queue depth
    axes[0].fill_between(ts, qs, alpha=0.25, color=PALETTE["red"])
    axes[0].plot(ts, qs, color=PALETTE["red"], linewidth=1.5)
    for i in range(len(ts)-1):
        if modes[i] == "ADAPTIVE":
            axes[0].axvspan(ts[i], ts[i+1], alpha=0.12, color=PALETTE["orange"])
    axes[0].axhline(300, color="red",   linestyle="--", alpha=0.5, label="HIGH threshold (300)")
    axes[0].axhline(100, color="green", linestyle="--", alpha=0.5, label="LOW threshold (100)")
    axes[0].set_ylabel("Queue Depth"); axes[0].legend(fontsize=8)
    axes[0].set_title("Queue Depth (orange shading = ADAPTIVE mode active)")

    # Normal vs Adaptive cumulative
    axes[1].plot(ts, norm, label="Normal (exact)",      color=PALETTE["blue"],  linewidth=1.5)
    axes[1].plot(ts, adap, label="Adaptive (prob)",     color=PALETTE["green"], linewidth=1.5)
    axes[1].fill_between(ts, norm, adap, alpha=0.1, color=PALETTE["green"])
    axes[1].set_ylabel("Cumulative Events"); axes[1].legend(fontsize=8)
    axes[1].set_title("Events Processed: Exact vs Probabilistic Mode")

    # Drops
    axes[2].fill_between(ts, drop, alpha=0.3, color=PALETTE["red"])
    axes[2].plot(ts, drop, color=PALETTE["red"], linewidth=1.5)
    axes[2].set_xlabel("Time (seconds)")
    axes[2].set_ylabel("Cumulative Drops")
    axes[2].set_title("Dropped Events (queue overflow during flash sale)")

    plt.tight_layout()
    fig.savefig(f"{OUT}/ecom_pipeline_timeline.png", dpi=150)
    plt.close(fig)
    print("ecom_pipeline_timeline.png")


# ── 2. HLL cardinality chart ──────────────────────────────────────────────
def hll_chart():
    print("  Running HLL cardinality benchmark …")
    checkpoints = [500, 1000, 2000, 5000, 10000, 20000, 50000]
    exact_users = set(); exact_products = set()
    hll_u = HLLCounter(p=12); hll_p = HLLCounter(p=12)

    eu_pts=[]; ep_pts=[]; hu_pts=[]; hp_pts=[]
    idx = 0
    N   = max(checkpoints)
    for i in range(N):
        ev  = generate_event()
        uid = ev["user_id"]; pid = ev["product_id"]
        exact_users.add(uid);    exact_products.add(pid)
        hll_u.add(uid);          hll_p.add(pid)
        if idx < len(checkpoints) and i+1 == checkpoints[idx]:
            eu_pts.append(len(exact_users));    ep_pts.append(len(exact_products))
            hu_pts.append(hll_u.count());       hp_pts.append(hll_p.count())
            idx += 1

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    fig.suptitle("HyperLogLog — Cardinality Estimation on E-Commerce Stream",
                 fontsize=13, fontweight="bold")

    for ax, ex, hx, label in [
        (axes[0], eu_pts, hu_pts, "Active Users"),
        (axes[1], ep_pts, hp_pts, "Unique Products Seen"),
    ]:
        ax.plot(checkpoints, ex, label="Exact",       color=PALETTE["blue"],  linewidth=2, marker="o")
        ax.plot(checkpoints, hx, label="HyperLogLog", color=PALETTE["green"], linewidth=2, marker="s", linestyle="--")
        ax.fill_between(checkpoints, ex, hx, alpha=0.1, color=PALETTE["red"])
        ax.set_xlabel("Events Processed"); ax.set_ylabel("Count"); ax.set_title(label)
        ax.legend()

    plt.tight_layout()
    fig.savefig(f"{OUT}/ecom_hll_cardinality.png", dpi=150)
    plt.close(fig)
    print("ecom_hll_cardinality.png")


# ── 3. Memory comparison ──────────────────────────────────────────────────
def memory_chart():
    import sys
    N = 100_000
    pv = defaultdict(int); users = set(); products = set()
    cm = CountMinSketch(epsilon=0.005, delta=0.01); hll_u = HLLCounter(); bloom = BloomMembership(capacity=500_000)

    for _ in range(N):
        ev = generate_event()
        pv[ev["product_id"]] += 1
        users.add(ev["user_id"]); products.add(ev["product_id"])
        cm.add(ev["product_id"]); hll_u.add(ev["user_id"]); bloom.add(ev["user_id"]+"::"+ev["product_id"])

    exact_kb = (sys.getsizeof(pv) + sys.getsizeof(users) + sys.getsizeof(products)) / 1024
    cm_kb    = sum(sys.getsizeof(r) for r in cm.table) / 1024
    hll_kb   = 2**12 / 1024
    bloom_kb = 500_000 * 1.44 / 8 / 1024

    labels = ["Exact\n(dict + sets)", "Count-Min\nSketch", "HyperLogLog\n(p=12)", "Bloom Filter\n(500K cap)"]
    values = [exact_kb, cm_kb, hll_kb, bloom_kb]
    colors = [PALETTE["red"], PALETTE["orange"], PALETTE["purple"], PALETTE["teal"]]

    fig, ax = plt.subplots(figsize=(9, 5))
    bars = ax.bar(labels, values, color=colors, width=0.5, edgecolor="white")
    for bar, val in zip(bars, values):
        ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+1,
                f"{val:.1f} KB", ha="center", va="bottom", fontweight="bold")
    ax.set_title("Memory Usage: Exact Structures vs Probabilistic (100K events)", fontsize=12)
    ax.set_ylabel("Memory (KB)")
    ax.set_ylim(0, max(values)*1.25)
    plt.tight_layout()
    fig.savefig(f"{OUT}/ecom_memory.png", dpi=150)
    plt.close(fig)
    print(f" ecom_memory.png  |  Exact={exact_kb:.1f}KB  CM={cm_kb:.1f}KB  HLL={hll_kb:.2f}KB  Bloom={bloom_kb:.1f}KB")


# ── 4. Bloom Filter FP rate chart ─────────────────────────────────────────
def bloom_fpr_chart():
    print("  Running Bloom FPR benchmark …")
    fpr_targets = [0.001, 0.005, 0.01, 0.02, 0.05, 0.1]
    observed_fpr = []
    N = 20_000; n_test = 5000

    for fpr in fpr_targets:
        b = BloomMembership(capacity=N, false_positive_rate=fpr)
        inserted = set()
        events = [generate_event() for _ in range(N)]
        for ev in events:
            key = f"{ev['user_id']}::{ev['product_id']}"
            b.add(key); inserted.add(key)

        fp = sum(1 for _ in range(n_test)
                 if (k := f"{random.choice(USERS)}::{random.choice(PRODUCTS)[0]}")
                 not in inserted and b.contains(k))
        observed_fpr.append(fp / n_test * 100)

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot([f*100 for f in fpr_targets], [f*100 for f in fpr_targets],
            label="Theoretical", color=PALETTE["grey"], linestyle="--", linewidth=1.5)
    ax.plot([f*100 for f in fpr_targets], observed_fpr,
            label="Observed", color=PALETTE["pink"], linewidth=2, marker="o")
    ax.set_xlabel("Target False Positive Rate (%)"); ax.set_ylabel("Observed FP Rate (%)")
    ax.set_title("Bloom Filter: Theoretical vs Observed False Positive Rate", fontsize=12)
    ax.legend(); plt.tight_layout()
    fig.savefig(f"{OUT}/ecom_bloom_fpr.png", dpi=150)
    plt.close(fig)
    print("ecom_bloom_fpr.png")


# ── main ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "="*55)
    print("  E-Commerce MTP Benchmark Suite")
    print("="*55)
    timeline_chart()
    hll_chart()
    memory_chart()
    bloom_fpr_chart()
    print(f"\n All charts saved to {OUT}/")
