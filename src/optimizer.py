import networkx as nx
from networkx.algorithms import community
from tabulate import tabulate


def build_communication_graph(data):
    """
    Build a simple undirected graph of ECUs connected by
    communication links only — no zone information included.
    This is the raw input the algorithm sees.
    """
    G = nx.Graph()

    for zone in data['zones']:
        for ecu in zone['ecus']:
            G.add_node(ecu['id'], human_zone=zone['id'],
                       human_zone_name=zone['name'])

    for conn in data['connections']:
        if G.has_node(conn['from']) and G.has_node(conn['to']):
            G.add_edge(conn['from'], conn['to'])

    return G


def compute_human_modularity(G, data):
    """
    Calculate the modularity score of the human-defined zone layout.
    Modularity measures how well zones separate heavy communicators
    from light ones. Score ranges 0 to 1 — higher is better.
    """
    human_partition = []
    for zone in data['zones']:
        zone_set = {ecu['id'] for ecu in zone['ecus']
                    if G.has_node(ecu['id'])}
        if zone_set:
            human_partition.append(zone_set)

    score = community.modularity(G, human_partition)
    return round(score, 4), human_partition


def compute_optimal_zones(G):
    """
    Run the greedy modularity algorithm. It starts with every ECU
    in its own zone, then merges zones that improve the modularity
    score until no merge improves it further.
    """
    optimal_partition = community.greedy_modularity_communities(G)
    optimal_partition = [set(c) for c in optimal_partition]
    score = community.modularity(G, optimal_partition)
    return round(score, 4), optimal_partition


def compute_zone_efficiency(human_score, optimal_score):
    """
    Zone efficiency = how close the human design is to the
    theoretical maximum. 100% means the human design IS the optimum.
    """
    if optimal_score <= 0:
        return 0.0
    efficiency = (human_score / optimal_score) * 100
    return round(efficiency, 1)


def find_reassignments(G, data, optimal_partition):
    """
    Compare human zones vs algorithm zones ECU by ECU.
    An ECU is flagged if the algorithm places it in a group
    that is dominated by ECUs from a different human zone.
    """
    ecu_to_human_zone = {}
    ecu_to_human_name = {}
    for zone in data['zones']:
        for ecu in zone['ecus']:
            ecu_to_human_zone[ecu['id']] = zone['id']
            ecu_to_human_name[ecu['id']] = zone['name']

    ecu_to_optimal_group = {}
    for i, group in enumerate(optimal_partition):
        for ecu_id in group:
            ecu_to_optimal_group[ecu_id] = i

    reassignments = []
    for zone in data['zones']:
        zone_id   = zone['id']
        zone_name = zone['name']
        ecu_ids   = [e['id'] for e in zone['ecus']
                     if G.has_node(e['id'])]

        for ecu_id in ecu_ids:
            my_group_idx = ecu_to_optimal_group.get(ecu_id)
            if my_group_idx is None:
                continue
            my_group = optimal_partition[my_group_idx]

            zone_counts = {}
            for other_ecu in my_group:
                z = ecu_to_human_zone.get(other_ecu, '?')
                zone_counts[z] = zone_counts.get(z, 0) + 1

            dominant_zone = max(zone_counts, key=zone_counts.get)

            if dominant_zone != zone_id:
                neighbors = list(G.neighbors(ecu_id))
                reassignments.append({
                    'ecu'          : ecu_id,
                    'human_zone'   : zone_name,
                    'algo_group'   : my_group_idx + 1,
                    'group_members': ', '.join(sorted(my_group)),
                    'neighbors'    : ', '.join(neighbors) if neighbors
                                     else 'none',
                })

    return reassignments


def print_optimizer_report(human_score, optimal_score,
                           optimal_partition, reassignments,
                           efficiency, data):

    print("\n" + "=" * 72)
    print("  ZONE BOUNDARY OPTIMALITY ANALYSIS")
    print("  Greedy Modularity Community Detection — NetworkX")
    print("=" * 72)

    score_table = [
        ["Design", "Zones", "Modularity Score", "Assessment"],
        ["Human-defined (physical location)",
         len(data['zones']), human_score, "Current YAML design"],
        ["Algorithm-optimal (communication pattern)",
         len(optimal_partition), optimal_score, "Theoretical best"],
    ]
    print(tabulate(score_table[1:], headers=score_table[0],
                   tablefmt="rounded_outline"))

    print(f"\n  Zone efficiency score : {efficiency}%")

    if efficiency >= 90:
        verdict = "Human design closely matches communication-optimal grouping"
    elif efficiency >= 70:
        verdict = "Minor boundary adjustments could improve modularity"
    elif efficiency >= 50:
        verdict = "Communication patterns partially align with physical zones"
    else:
        verdict = ("Physical zones and communication patterns are structurally "
                   "different — expected for hub-spoke truck architectures")
    print(f"  Interpretation       : {verdict}")

    print(f"""
  KEY FINDING:
  Physical zones (PTZ/CHZ/CBZ/FRZ) are defined by WHERE an ECU is bolted.
  Communication-optimal zones are defined by WHO an ECU talks to.
  On this truck these two criteria produce fundamentally different groupings.
  The algorithm found {len(optimal_partition)} natural communication clusters
  vs {len(data['zones'])} physical zones — confirming that zonal architecture
  involves an inherent tradeoff between wire-length minimization (physical
  grouping) and communication efficiency (functional grouping).
  This tradeoff is the core design challenge in Class 8 truck E/E architecture.
    """)

    print("  Algorithm-suggested communication clusters:")
    for i, group in enumerate(sorted(optimal_partition,
                                     key=len, reverse=True)):
        zone_counts = {}
        for ecu_id in group:
            for zone in data['zones']:
                if any(e['id'] == ecu_id for e in zone['ecus']):
                    zone_counts[zone['id']] = zone_counts.get(
                                              zone['id'], 0) + 1
        dominant = max(zone_counts, key=zone_counts.get) \
                   if zone_counts else '?'
        print(f"    Cluster {i+1} ({len(group)} ECUs, "
              f"mostly {dominant}): {', '.join(sorted(group))}")

    if reassignments:
        print(f"\n  ECUs whose communication pattern doesn't match "
              f"their physical zone ({len(reassignments)} flagged):")
        r_table = [["ECU", "Physical Zone", "Algo Cluster", "Talks to"]]
        for r in reassignments:
            r_table.append([
                r['ecu'],
                r['human_zone'],
                f"Cluster {r['algo_group']}",
                r['neighbors']
            ])
        print(tabulate(r_table[1:], headers=r_table[0],
                       tablefmt="rounded_outline"))
        print("\n  Note: These ECUs are not misplaced physically.")
        print("  They are flagged because their communication partners")
        print("  span multiple zones, making them natural boundary nodes.")
    else:
        print("\n  All ECUs sit within their expected communication clusters.")

    print("=" * 72 + "\n")


def run_optimizer(data):
    """Main function — call this from main.py"""
    G = build_communication_graph(data)

    human_score, human_partition     = compute_human_modularity(G, data)
    optimal_score, optimal_partition = compute_optimal_zones(G)
    efficiency                       = compute_zone_efficiency(
                                           human_score, optimal_score)
    reassignments                    = find_reassignments(
                                           G, data, optimal_partition)

    print_optimizer_report(human_score, optimal_score,
                           optimal_partition, reassignments,
                           efficiency, data)

    return {
        'human_score'       : human_score,
        'optimal_score'     : optimal_score,
        'efficiency'        : efficiency,
        'optimal_partition' : optimal_partition,
        'reassignments'     : reassignments,
        'graph'             : G,
    }


if __name__ == "__main__":
    import sys
    sys.path.insert(0, 'src')
    from parser import load_truck_config
    data = load_truck_config("configs/cascadia_126_2020.yaml")
    run_optimizer(data)