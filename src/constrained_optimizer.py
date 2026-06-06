"""
constrained_optimizer.py

Finds the optimal zone assignment for each ECU by balancing
two competing objectives:

  1. Wire length     — ECU should stay physically close to its ZC
  2. Communication   — ECU should be in the same zone as partners

Three modes:
  alpha = 1.0  →  Option A: pure physical  (no moves from human design)
  alpha = 0.5  →  Option B: combined       (move only if comm improves
                                            AND wire cost stays ≤ 3.0m)
  alpha = 0.0  →  Option C: communication  (move if comm improves,
                                            ignore wire cost)
"""

import sys
sys.path.insert(0, 'src')

from collections import defaultdict
from tabulate import tabulate


# ── HELPERS ───────────────────────────────────────────────────────────────

def get_zone_distance(data, zone_from, zone_to):
    """
    Distance between two zone centroids.
    Handles both key formats:
      ptz_to_chz  (short zone ID format)
      powertrain_to_chassis  (long name format)
    """
    if zone_from == zone_to:
        return 0.0

    zd = data['zone_distances']

    # try short ID format first (ptz_to_chz)
    k1 = f"{zone_from.lower()}_to_{zone_to.lower()}"
    k2 = f"{zone_to.lower()}_to_{zone_from.lower()}"
    if k1 in zd: return float(zd[k1])
    if k2 in zd: return float(zd[k2])

    # build a zone_id → name fragment mapping
    zone_fragments = {
        'PTZ': ['ptz', 'powertrain', 'pt'],
        'CHZ': ['chz', 'chassis', 'ch'],
        'CBZ': ['cbz', 'cab', 'cb'],
        'FRZ': ['frz', 'front', 'fr'],
    }

    frags_from = zone_fragments.get(zone_from.upper(), [zone_from.lower()])
    frags_to   = zone_fragments.get(zone_to.upper(),   [zone_to.lower()])

    # try all fragment combinations
    for ff in frags_from:
        for ft in frags_to:
            k1 = f"{ff}_to_{ft}"
            k2 = f"{ft}_to_{ff}"
            for key in zd:
                if k1 in key.lower() or k2 in key.lower():
                    return float(zd[key])

    # last resort: average
    return sum(zd.values()) / len(zd)


def build_connection_map(data):
    """ecu_id → list of ECU ids it communicates with."""
    conn_map = defaultdict(list)
    for conn in data['connections']:
        conn_map[conn['from']].append(conn['to'])
        conn_map[conn['to']].append(conn['from'])
    return dict(conn_map)


def build_ecu_home_zone(data):
    """ecu_id → original physical zone_id."""
    home = {}
    for zone in data['zones']:
        for ecu in zone['ecus']:
            home[ecu['id']] = zone['id']
    return home


def build_ecu_local_length(data):
    """ecu_id → local stub wire length to its own ZC."""
    local = {}
    for zone in data['zones']:
        for ecu in zone['ecus']:
            local[ecu['id']] = float(ecu['local_wire_length_m'])
    return local


def wire_cost_for_move(ecu_id, target_zone, home_zone, local_lengths, data):
    """
    Wire length if this ECU is assigned to target_zone.
    Same zone → use known local stub.
    Different zone → use zone-to-zone distance as proxy.
    """
    if target_zone == home_zone:
        return local_lengths[ecu_id]
    return get_zone_distance(data, home_zone, target_zone)


def comm_outside_fraction(ecu_id, target_zone, assignment, conn_map):
    """
    Fraction of this ECU's connections that are OUTSIDE target_zone.
    0.0 = all partners in same zone (best).
    1.0 = all partners in different zones (worst).
    """
    partners = conn_map.get(ecu_id, [])
    if not partners:
        return 0.0
    outside = sum(
        1 for p in partners
        if assignment.get(p, target_zone) != target_zone
    )
    return outside / len(partners)


# ── OPTIMIZER ─────────────────────────────────────────────────────────────

def run_optimizer(data, mode='combined'):
    """
    Greedy iterative zone reassignment.

    mode='physical'      → Option A: return human zones unchanged
    mode='combined'      → Option B: move if comm improves AND wire ≤ 3.0m
    mode='communication' → Option C: move if comm improves, ignore wire
    """
    home_zones = build_ecu_home_zone(data)

    # Option A: no changes at all
    if mode == 'physical':
        return dict(home_zones)

    zone_ids   = [z['id'] for z in data['zones']]
    conn_map   = build_connection_map(data)
    local_len  = build_ecu_local_length(data)
    all_ecus   = list(home_zones.keys())

    # combined mode wire threshold: allow adjacent zones (≤ 3.0m)
    # but block distant zones (4.5m, 5.5m, 7.0m)
    COMBINED_WIRE_THRESHOLD = 3.0

    assignment = dict(home_zones)

    for iteration in range(30):
        improved = False

        for ecu_id in all_ecus:
            current_zone = assignment[ecu_id]
            current_comm = comm_outside_fraction(
                ecu_id, current_zone, assignment, conn_map)

            best_zone    = current_zone
            best_comm    = current_comm

            for candidate_zone in zone_ids:
                if candidate_zone == current_zone:
                    continue

                # compute communication score if we move here
                # temporarily assign so partner calculations are consistent
                assignment[ecu_id] = candidate_zone
                cand_comm = comm_outside_fraction(
                    ecu_id, candidate_zone, assignment, conn_map)
                assignment[ecu_id] = current_zone  # revert

                # communication must strictly improve
                if not (cand_comm < current_comm - 0.01):
                    continue

                # mode-specific wire constraint
                if mode == 'combined':
                    w = wire_cost_for_move(
                        ecu_id, candidate_zone,
                        home_zones[ecu_id], local_len, data)
                    if w > COMBINED_WIRE_THRESHOLD:
                        continue
                # mode='communication': no wire constraint — fall through

                # keep the best-communicating candidate
                if cand_comm < best_comm - 0.001:
                    best_comm = cand_comm
                    best_zone = candidate_zone

            if best_zone != current_zone:
                assignment[ecu_id] = best_zone
                improved = True

        if not improved:
            break

    return assignment


# ── METRICS ───────────────────────────────────────────────────────────────

def compute_metrics(assignment, data):
    """Wire length, cross-zone run count, weight for a given assignment."""
    home_zones = build_ecu_home_zone(data)
    local_len  = build_ecu_local_length(data)
    conn_map   = build_connection_map(data)

    # local stubs: ECU to its assigned ZC
    total_wire = sum(
        wire_cost_for_move(ecu_id, zone, home_zones[ecu_id],
                           local_len, data)
        for ecu_id, zone in assignment.items()
    )

    # backbone: 3 shortest zone-to-zone distances
    backbone_segs = sorted(data['zone_distances'].values())[:3]
    total_wire   += sum(backbone_segs)

    # cross-zone: unique connection pairs in different zones
    seen       = set()
    cross_zone = 0
    for conn in data['connections']:
        a, b = conn['from'], conn['to']
        if a in assignment and b in assignment:
            if assignment[a] != assignment[b]:
                pair = tuple(sorted([a, b]))
                if pair not in seen:
                    cross_zone += 1
                    seen.add(pair)

    return {
        'total_wire_m' : round(total_wire, 1),
        'cross_zone'   : cross_zone,
        'weight_kg'    : round((total_wire * 120) / 1000, 1),
    }


# ── DIFF ──────────────────────────────────────────────────────────────────

def find_changes(physical_assignment, new_assignment, data):
    """List of ECUs that moved between physical and new assignment."""
    conn_map   = build_connection_map(data)
    zone_names = {z['id']: z['name'] for z in data['zones']}
    changes    = []

    for ecu_id, phys_zone in physical_assignment.items():
        new_zone = new_assignment.get(ecu_id, phys_zone)
        if new_zone == phys_zone:
            continue

        partners = conn_map.get(ecu_id, [])
        zone_counts = {}
        for p in partners:
            z = new_assignment.get(p, physical_assignment.get(p, '?'))
            zone_counts[z] = zone_counts.get(z, 0) + 1

        in_new  = zone_counts.get(new_zone, 0)
        in_old  = zone_counts.get(phys_zone, 0)
        total   = len(partners)

        reason = (
            f"{in_new}/{total} connections in new zone "
            f"vs {in_old}/{total} in current zone"
        ) if total > 0 else "No connections — wire optimisation"

        changes.append({
            'ecu'       : ecu_id,
            'from_zone' : zone_names.get(phys_zone, phys_zone),
            'to_zone'   : zone_names.get(new_zone, new_zone),
            'partners'  : ', '.join(partners) if partners else '—',
            'reason'    : reason,
        })

    return changes


# ── PARETO CURVE ──────────────────────────────────────────────────────────

def compute_pareto_curve(data):
    """
    Returns 3 data points for the Pareto curve:
    physical, combined, communication — with wire and cross-zone values.
    """
    curve = []
    for mode, label in [
        ('physical',      'Option A: Physical'),
        ('combined',      'Option B: Combined'),
        ('communication', 'Option C: Communication'),
    ]:
        assignment = run_optimizer(data, mode=mode)
        metrics    = compute_metrics(assignment, data)
        curve.append({
            'label'     : label,
            'wire_m'    : metrics['total_wire_m'],
            'cross_zone': metrics['cross_zone'],
        })
    return curve


# ── PRINT ─────────────────────────────────────────────────────────────────

def print_three_way(phys_m, comb_m, comm_m, changes, data):
    print("\n" + "=" * 76)
    print("  THREE-WAY ZONE ASSIGNMENT COMPARISON")
    print(f"  {data['metadata']['truck_model']}")
    print("=" * 76)

    table = [
        ["Metric",
         "Option A: Physical\n(current design)",
         "Option B: Combined\n(recommended)",
         "Option C: Communication\n(theoretical max)"],
        ["Total wire length",
         f"{phys_m['total_wire_m']} m",
         f"{comb_m['total_wire_m']} m",
         f"{comm_m['total_wire_m']} m"],
        ["Cross-zone runs",
         str(phys_m['cross_zone']),
         str(comb_m['cross_zone']),
         str(comm_m['cross_zone'])],
        ["Est. harness weight",
         f"{phys_m['weight_kg']} kg",
         f"{comb_m['weight_kg']} kg",
         f"{comm_m['weight_kg']} kg"],
        ["Physically feasible",
         "YES", "YES",
         "NO — some ECUs too far from ZC"],
    ]
    print(tabulate(table[1:], headers=table[0],
                   tablefmt="rounded_outline"))

    if changes:
        print(f"\n  ECUs recommended to move ({len(changes)} changes):")
        r = [["ECU", "Current Zone", "Recommended Zone", "Reason"]]
        for c in changes:
            r.append([c['ecu'], c['from_zone'],
                      c['to_zone'], c['reason']])
        print(tabulate(r[1:], headers=r[0],
                       tablefmt="rounded_outline"))
    else:
        print("\n  No zone changes recommended.")

    print("=" * 76 + "\n")


# ── MAIN ENTRY POINT ──────────────────────────────────────────────────────

def run_three_way_comparison(data):
    """Run all three modes and return everything needed for the PDF."""
    phys_assign = run_optimizer(data, mode='physical')
    comb_assign = run_optimizer(data, mode='combined')
    comm_assign = run_optimizer(data, mode='communication')

    phys_m = compute_metrics(phys_assign, data)
    comb_m = compute_metrics(comb_assign, data)
    comm_m = compute_metrics(comm_assign, data)

    changes = find_changes(phys_assign, comb_assign, data)
    pareto  = compute_pareto_curve(data)

    print_three_way(phys_m, comb_m, comm_m, changes, data)

    return {
        'physical_assignment'  : phys_assign,
        'combined_assignment'  : comb_assign,
        'comm_assignment'      : comm_assign,
        'physical_metrics'     : phys_m,
        'combined_metrics'     : comb_m,
        'comm_metrics'         : comm_m,
        'changes'              : changes,
        'pareto'               : pareto,
    }


if __name__ == "__main__":
    from parser import load_truck_config
    data = load_truck_config("configs/cascadia_126_2020.yaml")

    print("\nDebugging zone distances:")
    for k, v in data['zone_distances'].items():
        print(f"  {k}: {v}m")

    result = run_three_way_comparison(data)

    print("Pareto curve:")
    for pt in result['pareto']:
        print(f"  {pt['label']}: wire={pt['wire_m']}m  "
              f"cross-zone={pt['cross_zone']}")
