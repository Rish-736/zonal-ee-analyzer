"""
Stage-2 walking skeleton: the thinnest TSN simulator that connects to the
analyzer's zonal topology and produces real timing numbers.

What it does NOT do yet (deliberately): no priorities, no gate scheduling,
no preemption, no clock sync. Just: build graph -> route streams ->
serialize frames on each link -> measure end-to-end latency vs deadline.
Get THIS running first, then layer TSN behavior on top.

Run:  python simulate_min.py tsn_cascadia_min.yaml
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
    """Reuse point: later, swap this for the analyzer's graph.py zonal graph."""
    G = nx.Graph()
    for link in cfg["network"]["links"]:
        G.add_edge(link["src"], link["dst"],
                   rate_mbps=link["rate_mbps"], delay_us=link["delay_us"])
    return G


def transmission_ms(payload_bytes, rate_mbps):
    # bits / Mbps -> ms.  e.g. 64 B @ 100 Mbps = 0.00512 ms
    return (payload_bytes * 8) / (rate_mbps * 1000.0)


class Sim:
    def __init__(self, env, G):
        self.env = env
        self.G = G
        # one server per link => frames serialize (only one transmits at a time)
        self.links = {frozenset(e): simpy.Resource(env, capacity=1) for e in G.edges()}
        self.results = defaultdict(list)  # stream_id -> [end_to_end_latency_ms]

    def send_frame(self, stream, path):
        release = self.env.now
        for u, v in zip(path[:-1], path[1:]):
            edge = self.G[u][v]
            link = self.links[frozenset((u, v))]
            with link.request() as req:          # wait for the link to be free
                yield req
                yield self.env.timeout(transmission_ms(stream["payload_bytes"], edge["rate_mbps"]))
            yield self.env.timeout(edge["delay_us"] / 1000.0)   # propagation (does not block link)
        self.results[stream["id"]].append(self.env.now - release)

    def stream_process(self, stream):
        path = nx.shortest_path(self.G, stream["src"], stream["dst"])
        while True:
            self.env.process(self.send_frame(stream, path))
            yield self.env.timeout(stream["period_ms"])


def run(config_path, sim_time_ms=1000):
    cfg = load_config(config_path)
    G = build_graph(cfg)
    env = simpy.Environment()
    sim = Sim(env, G)
    for s in cfg["streams"]:
        env.process(sim.stream_process(s))
    env.run(until=sim_time_ms)

    streams = {s["id"]: s for s in cfg["streams"]}
    print(f"\nSimulated {sim_time_ms:.0f} ms\n")
    print(f"{'stream':<14}{'frames':>7}{'avg ms':>9}{'max ms':>9}{'deadline':>10}{'misses':>8}")
    print("-" * 57)
    for sid, lats in sim.results.items():
        dl = streams[sid]["deadline_ms"]
        misses = sum(1 for l in lats if l > dl)
        verdict = "OK" if misses == 0 else "FAIL"
        print(f"{sid:<14}{len(lats):>7}{sum(lats)/len(lats):>9.4f}{max(lats):>9.4f}"
              f"{dl:>10.1f}{misses:>6} {verdict}")


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "tsn_cascadia_min.yaml")
