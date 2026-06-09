import sys
import argparse
import yaml

sys.path.insert(0, 'src')

from parser   import load_truck_config
from graph    import build_legacy_graph, build_zonal_graph
from metrics  import calculate_metrics, print_metrics
from visualize import draw_legacy, draw_zonal, draw_comparison


def run_stage1(config_path):
    data    = load_truck_config(config_path)
    legacy  = build_legacy_graph(data)
    zonal   = build_zonal_graph(data)
    metrics = calculate_metrics(legacy, zonal, data)
    print_metrics(metrics)
    print("\nGenerating diagrams...")
    draw_legacy(legacy)
    draw_zonal(zonal, data)
    draw_comparison()
    print("\nDone. Check the outputs/ folder.")


def run_stage2(config_path):
    from tsn.simulator import run_tsn_analysis, print_results

    with open(config_path) as f:
        cfg = yaml.safe_load(f)

    tsn_cfg = cfg.get("tsn", cfg)

    if "streams" not in tsn_cfg:
        print("[Stage 2] No 'tsn:' block found in config. Skipping.")
        return

    print(f"\n[Stage 2] Simulating {len(tsn_cfg['streams'])} streams "
          f"on {len(tsn_cfg['links'])} links for 1000 ms ...\n")

    results = run_tsn_analysis(tsn_cfg, sim_time_ms=1000)
    print_results(results, tsn_cfg["streams"])

    # Headline summary
    print("\n── Headline Result ──────────────────────────────────────────")
    safety_streams = [s["id"] for s in tsn_cfg["streams"] if s["priority"] >= 6]
    for sid in safety_streams:
        fifo_max = results["fifo"][sid]["max_ms"]
        pre_max  = results["preemption"][sid]["max_ms"]
        status   = "PROTECTED" if results["preemption"][sid]["pass"] else "STILL FAILING"
        print(f"  {sid}: {fifo_max:.1f} ms (no TSN) → {pre_max:.3f} ms (TSN+preemption)  [{status}]")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Zonal E/E Analyzer + TSN Simulator")
    parser.add_argument("--config", default="configs/cascadia_126_2020.yaml",
                        help="Path to vehicle YAML config")
    parser.add_argument("--stage", choices=["analyze", "tsn", "full"], default="analyze",
                        help="analyze = Stage 1 only | tsn = Stage 2 only | full = both")
    args = parser.parse_args()

    if args.stage in ("analyze", "full"):
        run_stage1(args.config)

    if args.stage in ("tsn", "full"):
        run_stage2(args.config)
