import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import networkx as nx
import os

ZONE_COLORS = {
    'PTZ': '#E8604C',   # red-orange  — powertrain
    'CHZ': '#F5A623',   # amber       — chassis
    'CBZ': '#4A90D9',   # blue        — cab
    'FRZ': '#27AE60',   # green       — front
}
CONTROLLER_COLOR = '#2C3E50'  # dark slate for zone controllers
BACKBONE_COLOR   = '#2C3E50'

os.makedirs('outputs', exist_ok=True)

# ── helper ──────────────────────────────────────────────────────────────────
def zone_of(G, node):
    return G.nodes[node].get('zone', 'CBZ')

# ── DIAGRAM 1: Legacy topology ───────────────────────────────────────────────
def draw_legacy(legacy_graph):
    G = legacy_graph
    fig, ax = plt.subplots(figsize=(14, 10))
    ax.set_facecolor('#F8F9FA')
    fig.patch.set_facecolor('#F8F9FA')

    pos = nx.kamada_kawai_layout(G, scale=2.5)

    node_colors = [ZONE_COLORS.get(zone_of(G, n), '#999') for n in G.nodes()]

    # draw edges first (behind nodes)
    cross_edges = [(u, v) for u, v, d in G.edges(data=True) if d['weight'] > 0.5]
    intra_edges = [(u, v) for u, v, d in G.edges(data=True) if d['weight'] <= 0.5]

    nx.draw_networkx_edges(G, pos, edgelist=cross_edges,
                           edge_color='#CC0000', alpha=0.5, width=1.2, ax=ax)
    nx.draw_networkx_edges(G, pos, edgelist=intra_edges,
                           edge_color='#888888', alpha=0.4, width=0.8, ax=ax)

    nx.draw_networkx_nodes(G, pos, node_color=node_colors,
                           node_size=600, ax=ax)
    nx.draw_networkx_labels(G, pos, font_size=7,
                            font_weight='bold', font_color='white', ax=ax)

    # legend
    legend_handles = [
        mpatches.Patch(color=ZONE_COLORS['PTZ'], label='Powertrain Zone (PTZ)'),
        mpatches.Patch(color=ZONE_COLORS['CHZ'], label='Chassis Zone (CHZ)'),
        mpatches.Patch(color=ZONE_COLORS['CBZ'], label='Cab Zone (CBZ)'),
        mpatches.Patch(color=ZONE_COLORS['FRZ'], label='Front Zone (FRZ)'),
        mpatches.Patch(color='#CC0000', label='Cross-zone wire run'),
        mpatches.Patch(color='#888888', label='Intra-zone wire run'),
    ]
    ax.legend(handles=legend_handles, loc='lower left', fontsize=8,
              framealpha=0.9, edgecolor='#CCCCCC')

    ax.set_title('Legacy Point-to-Point Architecture\n'
                 '22 ECUs | 25 connections | 52.5 m total wire | 16 cross-zone runs',
                 fontsize=13, fontweight='bold', pad=16, color='#2C3E50')
    ax.axis('off')
    plt.tight_layout()
    plt.savefig('outputs/legacy_topology.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("  Saved: outputs/legacy_topology.png")


# ── DIAGRAM 2: Zonal topology ────────────────────────────────────────────────
def draw_zonal(zonal_graph, data):
    G = zonal_graph
    fig, ax = plt.subplots(figsize=(14, 10))
    ax.set_facecolor('#F8F9FA')
    fig.patch.set_facecolor('#F8F9FA')

    # manual layout: place zone controllers in a line, ECUs around them
    zone_positions = {
        'PTZ': (-3.0, 0),
        'CHZ': (-1.0, 0),
        'CBZ': ( 1.0, 0),
        'FRZ': ( 3.0, 0),
    }
    controllers = {z['zone_controller']: z['id'] for z in data['zones']}
    pos = {}

    # position zone controllers
    for zc, zid in controllers.items():
        pos[zc] = zone_positions[zid]

    # position ECUs around their zone controller in a circle
    import math
    zone_ecus = {z['id']: [e['id'] for e in z['ecus']] for z in data['zones']}
    for zid, ecus in zone_ecus.items():
        cx, cy = zone_positions[zid]
        n = len(ecus)
        radius = 1.1 if n > 4 else 0.85
        for i, ecu in enumerate(ecus):
            angle = (2 * math.pi * i / n) - math.pi / 2
            pos[ecu] = (cx + radius * math.cos(angle),
                        cy + radius * math.sin(angle))

    # backbone edges (between zone controllers)
    backbone_edges = [(u, v) for u, v, d in G.edges(data=True)
                      if d.get('is_backbone')]
    local_edges    = [(u, v) for u, v, d in G.edges(data=True)
                      if not d.get('is_backbone')]

    nx.draw_networkx_edges(G, pos, edgelist=backbone_edges,
                           edge_color=BACKBONE_COLOR, width=3.5,
                           alpha=0.85, ax=ax, style='solid')
    nx.draw_networkx_edges(G, pos, edgelist=local_edges,
                           edge_color='#AAAAAA', width=1.0,
                           alpha=0.6, ax=ax)

    # ECU nodes
    ecu_nodes  = [n for n in G.nodes() if not G.nodes[n].get('is_controller')]
    ecu_colors = [ZONE_COLORS.get(zone_of(G, n), '#999') for n in ecu_nodes]
    nx.draw_networkx_nodes(G, pos, nodelist=ecu_nodes,
                           node_color=ecu_colors, node_size=500, ax=ax)
    nx.draw_networkx_labels(G, pos,
                            labels={n: n for n in ecu_nodes},
                            font_size=6.5, font_weight='bold',
                            font_color='white', ax=ax)

    # Zone controller nodes (larger, dark)
    zc_nodes = [n for n in G.nodes() if G.nodes[n].get('is_controller')]
    nx.draw_networkx_nodes(G, pos, nodelist=zc_nodes,
                           node_color=CONTROLLER_COLOR,
                           node_size=1200, ax=ax)
    nx.draw_networkx_labels(G, pos,
                            labels={n: n for n in zc_nodes},
                            font_size=7.5, font_weight='bold',
                            font_color='white', ax=ax)

    legend_handles = [
        mpatches.Patch(color=ZONE_COLORS['PTZ'], label='Powertrain Zone (PTZ)'),
        mpatches.Patch(color=ZONE_COLORS['CHZ'], label='Chassis Zone (CHZ)'),
        mpatches.Patch(color=ZONE_COLORS['CBZ'], label='Cab Zone (CBZ)'),
        mpatches.Patch(color=ZONE_COLORS['FRZ'], label='Front Zone (FRZ)'),
        mpatches.Patch(color=CONTROLLER_COLOR,   label='Zone Controller'),
        mpatches.Patch(color=BACKBONE_COLOR,     label='Ethernet Backbone'),
    ]
    ax.legend(handles=legend_handles, loc='lower left', fontsize=8,
              framealpha=0.9, edgecolor='#CCCCCC')

    ax.set_title('Zonal Architecture (4-Zone)\n'
                 '22 ECUs + 4 Zone Controllers | 24.3 m total wire | 3 backbone segments',
                 fontsize=13, fontweight='bold', pad=16, color='#2C3E50')
    ax.axis('off')
    plt.tight_layout()
    plt.savefig('outputs/zonal_topology.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("  Saved: outputs/zonal_topology.png")


# ── DIAGRAM 3: Comparison bar chart ─────────────────────────────────────────
def draw_comparison():
    fig, axes = plt.subplots(1, 3, figsize=(14, 6))
    fig.patch.set_facecolor('#F8F9FA')

    metrics = [
        {
            'ax'     : axes[0],
            'title'  : 'Cross-Zone Wire Runs',
            'unit'   : 'connections',
            'legacy' : 16,
            'zonal'  : 3,
            'pct'    : '81.2%',
        },
        {
            'ax'     : axes[1],
            'title'  : 'Total Wire Length',
            'unit'   : 'meters',
            'legacy' : 52.5,
            'zonal'  : 24.3,
            'pct'    : '53.7%',
        },
        {
            'ax'     : axes[2],
            'title'  : 'Est. Harness Weight',
            'unit'   : 'kg (signal wires)',
            'legacy' : 6.3,
            'zonal'  : 2.9,
            'pct'    : '53.7%',
        },
    ]

    for m in metrics:
        ax = m['ax']
        ax.set_facecolor('#F8F9FA')
        bars = ax.bar(['Legacy', 'Zonal'],
                      [m['legacy'], m['zonal']],
                      color=['#CC3333', '#27AE60'],
                      width=0.45, edgecolor='white', linewidth=1.2)

        # value labels on bars
        for bar, val in zip(bars, [m['legacy'], m['zonal']]):
            ax.text(bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + m['legacy'] * 0.02,
                    str(val), ha='center', va='bottom',
                    fontsize=11, fontweight='bold', color='#2C3E50')

        # reduction annotation
        ax.annotate(f'↓ {m["pct"]} reduction',
                    xy=(0.5, 0.92), xycoords='axes fraction',
                    ha='center', fontsize=10,
                    color='#27AE60', fontweight='bold')

        ax.set_title(m['title'], fontsize=12,
                     fontweight='bold', color='#2C3E50', pad=10)
        ax.set_ylabel(m['unit'], fontsize=9, color='#555555')
        ax.set_ylim(0, m['legacy'] * 1.25)
        ax.spines[['top', 'right']].set_visible(False)
        ax.tick_params(labelsize=10)
        ax.yaxis.grid(True, linestyle='--', alpha=0.5)
        ax.set_axisbelow(True)

    fig.suptitle('Zonal vs. Legacy Architecture — Freightliner Cascadia 126\n'
                 'Same 22 ECUs | Same 25 logical connections | Architecture change only',
                 fontsize=13, fontweight='bold', color='#2C3E50', y=1.02)
    plt.tight_layout()
    plt.savefig('outputs/comparison_chart.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("  Saved: outputs/comparison_chart.png")


# ── entry point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    sys.path.insert(0, 'src')
    from parser import load_truck_config
    from graph  import build_legacy_graph, build_zonal_graph

    data   = load_truck_config("configs/cascadia_126_2020.yaml")
    legacy = build_legacy_graph(data)
    zonal  = build_zonal_graph(data)

    print("\nGenerating diagrams...")
    draw_legacy(legacy)
    draw_zonal(zonal, data)
    draw_comparison()
    print("\nDone. Open the outputs/ folder to see your three diagrams.")