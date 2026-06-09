"""
simulate_v3.py — adds IEEE 802.1Qbu-style frame preemption.
When a high-priority frame (brake) arrives mid-transmission of a low-priority
frame (ADAS), it interrupts and takes the link immediately.
The interrupted frame restarts once the link is free again.

Run:  python simulate_v3.py tsn_cascadia_heavy.yaml
"""
import sys
from collections import defaultdict
import yaml, simpy, networkx as nx


def load_config(path):
    with open(path) as f:
        return yaml.safe_load(f)

def build_graph(cfg):
    G = nx.Graph()
    for l in cfg["network"]["links"]:
        G.add_edge(l["src"], l["dst"], rate_mbps=l["rate_mbps"], delay_us=l["delay_us"])
    return G

def tx_ms(payload_bytes, rate_mbps):
    return (payload_bytes * 8) / (rate_mbps * 1000.0)


class Sim:
    def __init__(self, env, G, mode="fifo"):
        self.env = env
        self.G = G
        self.mode = mode   # "fifo" | "priority" | "preemption"
        self.links = {frozenset(e): simpy.PreemptiveResource(env, capacity=1) for e in G.edges()}
        self.results = defaultdict(list)

    def queue_prio(self, stream):
        if self.mode == "fifo":
            return 0
        return 8 - stream["priority"]   # lower = served first in SimPy

    def send_frame(self, stream, path):
        release = self.env.now
        for u, v in zip(path[:-1], path[1:]):
            edge = self.G[u][v]
            link = self.links[frozenset((u, v))]
            prio = self.queue_prio(stream)
            do_preempt = (self.mode == "preemption")
            tx_time = tx_ms(stream["payload_bytes"], edge["rate_mbps"])

            # retry loop — frame may be preempted and must restart
            while True:
                req = link.request(priority=prio, preempt=do_preempt)
                yield req
                try:
                    yield self.env.timeout(tx_time)
                    link.release(req)
                    break           # transmission completed
                except simpy.Interrupt:
                    link.release(req)
                    # preempted mid-frame: restart transmission (simplified model)

            yield self.env.timeout(edge["delay_us"] / 1000.0)
        self.results[stream["id"]].append(self.env.now - release)

    def stream_process(self, stream):
        path = nx.shortest_path(self.G, stream["src"], stream["dst"])
        while True:
            self.env.process(self.send_frame(stream, path))
            yield self.env.timeout(stream["period_ms"])


def run_once(cfg, G, mode, sim_time_ms=1000):
    env = simpy.Environment()
    sim = Sim(env, G, mode=mode)
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
        print(f"{sid:<14}{len(lats):>7}{sum(lats)/len(lats):>10.3f}"
              f"{max(lats):>10.3f}{dl:>10.1f}{misses:>6} {v}")


if __name__ == "__main__":
    cfg = load_config(sys.argv[1] if len(sys.argv) > 1 else "tsn_cascadia_heavy.yaml")
    G = build_graph(cfg)
    report("WITHOUT TSN  (plain Ethernet, FIFO)",      cfg, run_once(cfg, G, "fifo"))
    report("WITH TSN     (priority scheduling)",        cfg, run_once(cfg, G, "priority"))
    report("WITH TSN     (priority + preemption)",      cfg, run_once(cfg, G, "preemption"))
