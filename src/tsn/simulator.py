"""
src/tsn/simulator.py
Stage 2 — TSN Scheduler Simulator

Plugs into the existing zonal-ee-analyzer pipeline.
Reads the `tsn:` block from any vehicle YAML config and runs three modes:
  fifo        → plain Ethernet, first-come-first-served
  priority    → TSN priority scheduling (IEEE 802.1Q)
  preemption  → priority + frame preemption (IEEE 802.1Qbu)

Usage (standalone):
    python -m src.tsn.simulator --config configs/cascadia_tsn_extension.yaml

Usage (from main.py pipeline):
    from src.tsn.simulator import run_tsn_analysis
    results = run_tsn_analysis(tsn_config)
"""

import argparse
from collections import defaultdict

import yaml
import simpy
import networkx as nx


# ── Graph builder ─────────────────────────────────────────────────────────────

def build_tsn_graph(tsn_cfg):
    """Build a NetworkX graph from the tsn: links block."""
    G = nx.Graph()
    for link in tsn_cfg["links"]:
        G.add_edge(link["src"], link["dst"],
                   rate_mbps=link["rate_mbps"],
                   delay_us=link["delay_us"])
    return G


# ── Simulation core ───────────────────────────────────────────────────────────

def tx_ms(payload_bytes, rate_mbps):
    """Transmission time in milliseconds."""
    return (payload_bytes * 8) / (rate_mbps * 1000.0)


class TSNSim:
    def __init__(self, env, G, mode="fifo"):
        self.env = env
        self.G = G
        self.mode = mode
        self.links = {
            frozenset(e): simpy.PreemptiveResource(env, capacity=1)
            for e in G.edges()
        }
        self.results = defaultdict(list)

    def _priority(self, stream):
        if self.mode == "fifo":
            return 0
        return 8 - stream["priority"]   # lower number = served first in SimPy

    def _send_frame(self, stream, path):
        release = self.env.now
        for u, v in zip(path[:-1], path[1:]):
            edge = self.G[u][v]
            link = self.links[frozenset((u, v))]
            prio = self._priority(stream)
            do_preempt = (self.mode == "preemption")
            tx_time = tx_ms(stream["payload_bytes"], edge["rate_mbps"])

            # Retry loop: frame restarts if preempted mid-transmission
            while True:
                req = link.request(priority=prio, preempt=do_preempt)
                try:
                    yield req
                except simpy.Interrupt:
                    # preempted while waiting in queue — retry
                    continue
                try:
                    yield self.env.timeout(tx_time)
                    link.release(req)
                    break
                except simpy.Interrupt:
                    link.release(req)
                    # preempted mid-transmission — restart (802.1Qbu simplified model)

            yield self.env.timeout(edge["delay_us"] / 1000.0)

        self.results[stream["id"]].append(self.env.now - release)

    def _stream_process(self, stream):
        path = nx.shortest_path(self.G, stream["src"], stream["dst"])
        while True:
            self.env.process(self._send_frame(stream, path))
            yield self.env.timeout(stream["period_ms"])


def _run_mode(tsn_cfg, G, mode, sim_time_ms):
    env = simpy.Environment()
    sim = TSNSim(env, G, mode=mode)
    for s in tsn_cfg["streams"]:
        env.process(sim._stream_process(s))
    env.run(until=sim_time_ms)
    return dict(sim.results)


# ── Public API (called by main.py) ────────────────────────────────────────────

def run_tsn_analysis(tsn_cfg, sim_time_ms=1000):
    """
    Run all three modes and return structured results.
    Called by main.py when --stage tsn or --stage full is used.

    Returns:
        dict with keys 'fifo', 'priority', 'preemption'
        each mapping stream_id -> {frames, avg_ms, max_ms, deadline_ms, misses, pass}
    """
    G = build_tsn_graph(tsn_cfg)
    stream_meta = {s["id"]: s for s in tsn_cfg["streams"]}
    output = {}

    for mode in ["fifo", "priority", "preemption"]:
        raw = _run_mode(tsn_cfg, G, mode, sim_time_ms)
        output[mode] = {}
        for sid, lats in raw.items():
            dl = stream_meta[sid]["deadline_ms"]
            misses = sum(1 for l in lats if l > dl)
            output[mode][sid] = {
                "frames":      len(lats),
                "avg_ms":      round(sum(lats) / len(lats), 4),
                "max_ms":      round(max(lats), 4),
                "deadline_ms": dl,
                "misses":      misses,
                "pass":        misses == 0,
            }

    return output


def print_results(results, streams):
    labels = {
        "fifo":       "WITHOUT TSN  (plain Ethernet)",
        "priority":   "WITH TSN     (priority scheduling)",
        "preemption": "WITH TSN     (priority + preemption)",
    }
    for mode, label in labels.items():
        print(f"\n=== {label} ===")
        print(f"{'stream':<16}{'frames':>7}{'avg ms':>10}{'max ms':>10}"
              f"{'deadline':>10}{'misses':>8}")
        print("-" * 62)
        for sid, r in results[mode].items():
            v = "OK" if r["pass"] else "FAIL"
            print(f"{sid:<16}{r['frames']:>7}{r['avg_ms']:>10.3f}"
                  f"{r['max_ms']:>10.3f}{r['deadline_ms']:>10.1f}"
                  f"{r['misses']:>6} {v}")


# ── Standalone entry point ────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TSN Scheduler Simulator — Stage 2")
    parser.add_argument("--config", required=True, help="Path to YAML with tsn: block")
    parser.add_argument("--time",   type=int, default=1000, help="Simulation time in ms")
    args = parser.parse_args()

    with open(args.config) as f:
        cfg = yaml.safe_load(f)

    tsn_cfg = cfg.get("tsn", cfg)   # supports both standalone and extended YAML
    results = run_tsn_analysis(tsn_cfg, sim_time_ms=args.time)
    print_results(results, tsn_cfg["streams"])
