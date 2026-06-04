from tabulate import tabulate

# A bundled truck signal harness averages ~120 g/m accounting for
# insulation, shielding, and multi-wire bundling (conservative estimate)
BUNDLE_WEIGHT_G_PER_M = 120

def calculate_metrics(legacy_graph, zonal_graph, data):
    legacy_length = sum(d['weight'] for _, _, d in legacy_graph.edges(data=True))
    zonal_length  = sum(d['weight'] for _, _, d in zonal_graph.edges(data=True))

    legacy_weight_kg = (legacy_length * BUNDLE_WEIGHT_G_PER_M) / 1000
    zonal_weight_kg  = (zonal_length  * BUNDLE_WEIGHT_G_PER_M) / 1000

    # Count meaningful long-distance runs in legacy
    # (same-zone connections are short, cross-zone are the problem)
    cross_zone_legacy = 0
    intra_zone_legacy = 0
    for u, v, d in legacy_graph.edges(data=True):
        if d['weight'] > 0.5:
            cross_zone_legacy += 1
        else:
            intra_zone_legacy += 1

    # In zonal: only the 3 backbone segments are long cross-zone runs
    cross_zone_zonal = 3  # the 4 zone controllers linked by backbone

    def pct_reduction(old, new):
        return round(((old - new) / old) * 100, 1)

    metrics = {
        'legacy_length_m'       : round(legacy_length, 1),
        'zonal_length_m'        : round(zonal_length, 1),
        'legacy_weight_kg'      : round(legacy_weight_kg, 1),
        'zonal_weight_kg'       : round(zonal_weight_kg, 1),
        'weight_saved_kg'       : round(legacy_weight_kg - zonal_weight_kg, 1),
        'cross_zone_legacy'     : cross_zone_legacy,
        'cross_zone_zonal'      : cross_zone_zonal,
        'length_reduction_pct'  : pct_reduction(legacy_length, zonal_length),
        'weight_reduction_pct'  : pct_reduction(legacy_weight_kg, zonal_weight_kg),
        'cross_zone_reduction_pct': pct_reduction(cross_zone_legacy, cross_zone_zonal),
    }
    return metrics

def print_metrics(metrics):
    table = [
        ["Metric",
         "Legacy (point-to-point)",
         "Zonal (4-zone)",
         "Reduction"],
        ["Cross-zone wire runs",
         metrics['cross_zone_legacy'],
         metrics['cross_zone_zonal'],
         f"{metrics['cross_zone_reduction_pct']}% fewer"],
        ["Total wire length",
         f"{metrics['legacy_length_m']} m",
         f"{metrics['zonal_length_m']} m",
         f"{metrics['length_reduction_pct']}% saved"],
        ["Est. harness weight*",
         f"{metrics['legacy_weight_kg']} kg",
         f"{metrics['zonal_weight_kg']} kg",
         f"{metrics['weight_saved_kg']} kg saved"],
    ]

    print("\n" + "=" * 72)
    print("  ZONAL E/E ARCHITECTURE — COMPARISON RESULTS")
    print("  Freightliner Cascadia 126 (2020) | 22 ECUs | 4 Zones")
    print("=" * 72)
    print(tabulate(table[1:], headers=table[0], tablefmt="rounded_outline"))
    print("=" * 72)
    print(f"\n  Wire length  : -{metrics['length_reduction_pct']}%  "
          f"({metrics['legacy_length_m']}m → {metrics['zonal_length_m']}m)")
    print(f"  Harness weight: -{metrics['weight_reduction_pct']}%  "
          f"({metrics['legacy_weight_kg']}kg → {metrics['zonal_weight_kg']}kg)")
    print(f"  Long cross-zone runs: {metrics['cross_zone_legacy']} → {metrics['cross_zone_zonal']}"
          f"  ({metrics['cross_zone_reduction_pct']}% reduction)")
    print("\n  * Weight estimate uses 120 g/m bundled harness average (signal wires)")
    print("    Same 22 ECUs. Same logical connections. Architecture change only.")
    print("=" * 72 + "\n")

if __name__ == "__main__":
    import sys
    sys.path.insert(0, 'src')
    from parser import load_truck_config
    from graph  import build_legacy_graph, build_zonal_graph

    data   = load_truck_config("configs/cascadia_126_2020.yaml")
    legacy = build_legacy_graph(data)
    zonal  = build_zonal_graph(data)

    metrics = calculate_metrics(legacy, zonal, data)
    print_metrics(metrics)