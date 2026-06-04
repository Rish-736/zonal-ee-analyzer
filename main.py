import sys
sys.path.insert(0, 'src')

from parser  import load_truck_config
from graph   import build_legacy_graph, build_zonal_graph
from metrics import calculate_metrics, print_metrics
from visualize import draw_legacy, draw_zonal, draw_comparison

if __name__ == "__main__":
    filepath = sys.argv[1] if len(sys.argv) > 1 else "configs/cascadia_126_2020.yaml"
    data     = load_truck_config(filepath)
    legacy   = build_legacy_graph(data)
    zonal    = build_zonal_graph(data)
    metrics  = calculate_metrics(legacy, zonal, data)
    print_metrics(metrics)
    print("\nGenerating diagrams...")
    draw_legacy(legacy)
    draw_zonal(zonal, data)
    draw_comparison()
    print("\nDone. Check the outputs/ folder.")