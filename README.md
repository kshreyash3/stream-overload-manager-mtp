# Stream Overload Manager

> An M.Tech project on Adaptive Load-Shedding using Probabilistic Data Structures. It implements a Smart Valve architecture that automatically switches to probabilistic algorithms during traffic spikes to prevent system failure while maintaining approximate query accuracy.

**Author:** Shreyash Kadam [M25DE1016]
**Institution:** IIT Jodhpur, M.Tech in Data Engineering

---

## Project Overview

Modern streaming applications often face unpredictable traffic spikes that can overwhelm processing capacity. Traditional systems either queue everything (causing unacceptable latency) or drop data (causing data loss).

This project introduces an intelligent Smart Valve load monitor. Under normal conditions, events are processed exactly. When incoming rates exceed consumer capacity and queues fill up, the system dynamically sheds load by transitioning into an Adaptive Mode. It routes queries to space-efficient probabilistic data structures to maintain high availability and acceptable error bounds.

---

## Repository Structure

* `outputs/`: Contains benchmark charts (e.g., FPR, cardinality, memory) and pipeline interval metrics.
* `benchmark.py`: Suite for generating performance charts and running evaluation metrics.
* `ecommerce_data.py`: Data simulation containing 590 products across 12 categories.
* `events.jsonl`: Sample streaming payload data.
* `load_monitor.py`: Smart Valve logic and queue threshold detection.
* `pipeline.py`: Core stream processing and routing logic.
* `prob_structures.py`: Implementations of CM Sketch, HLL, and Bloom Filters.
* `run_events.py`: Main execution script with CLI arguments.

---

## How to Run

**Run the Streaming Pipeline**
Execute the pipeline simulating a normal rate with a sudden flash sale spike (runs in Shadow Mode for deviation metrics):
`python3 run_events.py --count 500 --spike`

**Generate Benchmarks**
Run the evaluation suite and generate performance visualizations in the outputs folder:
`python3 benchmark.py`

---

## Key Results & Benchmarks

The system was evaluated under a simulated flash sale scenario transitioning from 500 ev/s to 4000 ev/s. The Smart Valve successfully detected queue saturation and transitioned to Adaptive Mode, maintaining target constraints of less than 5% query error.

**Query Accuracy (Probabilistic vs. Exact)**

| Metric | Algorithm | Error Rate / Result |
| :--- | :--- | :--- |
| Heavy Hitters (freq ≥ 50) | Count-Min Sketch | 0.10% MAPE |
| Top 3 Viewed/Ordered | Count-Min Sketch | 0.0% Error |
| Unique Users | HyperLogLog | 0.80% Error |
| Unique Products | HyperLogLog | 0.87% Error |
| False Negatives | Bloom Filter | 0 |
| Observed FPR | Bloom Filter | 0.0% |

**Memory Footprint Analysis**

| Data Structure | Memory Usage |
| :--- | :--- |
| Exact Processing | 82.5 KB |
| HyperLogLog | 4.00 KB |
| Bloom Filter | 87.9 KB |
| Count-Min Sketch | 781.8 KB |

---

## Core Architecture

* **Normal Mode:** Exact processing using standard data structures for full query accuracy.
* **Adaptive Mode:** Smart Valve redirects processing during overload conditions.
* **Count-Min Sketch:** Used for heavy-hitter frequency queries.
* **HyperLogLog:** Used for distinct count estimations.
* **Bloom Filters:** Used for fast membership queries.
