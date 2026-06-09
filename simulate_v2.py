"""
Stage-2 simulator, v2: adds priority scheduling (one TSN mechanism) and runs
the SAME network twice -- once as plain Ethernet (FIFO), once with TSN priority
-- so you can see the critical stream fail, then get rescued.

In SimPy a PriorityResource serves the lowest priority NUMBER first, so we map a
high stream priority (e.g. brake = 7) to a low number => it jumps the queue.

Run:  python simulate_v2.py tsn_cascadia_heavy.yaml
"""
import sys
from collections import defaultdict

import yaml
import simpy
import networkx as nx


def load_config(path):
    with open(path) as f:
        return yaml.safe_load(f)


def build_graph(cfg):
    G = nx.Graph()
    for link in cfg["network"]["links"]:
        G.add_edge(link["src"], link["dst"],
                   rate_mbps=link["rate_mbps"], delay_us=link["delay_us"])
    return G


def transmission_ms(payload_bytes, rate_mbps):
    return (payload_bytes * 8) / (rate_mbps * 1000.0)


class Sim:
    def __init__(self, env, G, tsn=False):
        self.env = env
        self.G = G
        self.tsn = tsn
        self.links = {frozenset(e): simpy.PriorityResource(env, capacity=1) for e in G.edges()}
        self.results = defaultdict(list)

    def queue_priority(self, stream):
        # TSN ON  -> high-priority streams get a low number => served first.
        # TSN OFF -> everyone equal => plain first-come-first-served.
        return (8 - stream["priority"]) if self.tsn else 0

    def send_frame(self, stream, path):
        release = self.env.now
        for u, v in zip(path[:-1], path[1:]):
            edge = self.G[u][v]
            link = self.links[frozenset((u, v))]
            with link.request(priority=self.queue_priority(stream)) as req:
                yield req
                yield self.env.timeout(transmission_ms(stream["payload_bytes"], edge["rate_mbps"]))
            yield self.env.timeout(edge["delay_us"] / 1000.0)
        self.results[stream["id"]].append(self.env.now - release)

    def stream_process(self, stream):
        path = nx.shortest_path(self.G, stream["src"], stream["dst"])
        while True:
            self.env.process(self.send_frame(stream, path))
            yield self.env.timeout(stream["period_ms"])


def run_once(cfg, G, tsn, sim_time_ms=1000):
    env = simpy.Environment()
    sim = Sim(env, G, tsn=tsn)
    for s in cfg["streams"]:
        env.process(sim.stream_process(s))
    env.run(until=sim_time_ms)
    return sim.results


def report(label, cfg, results):
    streams = {s["id"]: s for s in cfg["streams"]}
    print(f"\n=== {label} ===")
    print(f"{'stream':<14}{'frames':>7}{'avg ms':>10}{'max ms':>10}{'deadline':>10}{'misses':>8}")
    print("-" * 60)
    for sid, lats in results.items():
        dl = streams[sid]["deadline_ms"]
        misses = sum(1 for l in lats if l > dl)
        v = "OK" if misses == 0 else "FAIL"
        print(f"{sid:<14}{len(lats):>7}{sum(lats)/len(lats):>10.3f}{max(lats):>10.3f}"
              f"{dl:>10.1f}{misses:>6} {v}")


if __name__ == "__main__":
    cfg = load_config(sys.argv[1] if len(sys.argv) > 1 else "tsn_cascadia_heavy.yaml")
    G = build_graph(cfg)
    report("WITHOUT TSN  (plain Ethernet, first-come-first-served)", cfg, run_once(cfg, G, tsn=False))
    report("WITH TSN     (priority scheduling)", cfg, run_once(cfg, G, tsn=True))
