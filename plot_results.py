"""
Generates a visual comparison chart from the TSN simulator results.
Run AFTER simulate_v2.py to visualize the before/after.

Usage:  python plot_results.py
Output: tsn_comparison.html  (interactive)
        tsn_comparison.png   (static, for GitHub/report)
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ── Results hardcoded from simulate_v2.py output ──────────────────────────────
# Replace these numbers any time you re-run the simulator.
streams      = ["brake_cmd", "infotainment", "adas_flood"]
deadlines    = [2.0, 30.0, 50.0]

max_no_tsn   = [166.592, 0.237, 167.152]
max_with_tsn = [0.167,   0.237, 167.214]

misses_no_tsn   = [83,  0, 5843]
misses_with_tsn = [0,   0, 5843]

COLORS = {
    "no_tsn":   "#EF553B",   # red
    "with_tsn": "#00CC96",   # green
    "deadline": "#FFA15A",   # orange
}

# ── Build figure with two subplots ────────────────────────────────────────────
fig = make_subplots(
    rows=1, cols=2,
    subplot_titles=(
        "Worst-case Latency (ms) — lower is better",
        "Deadline Misses — lower is better"
    ),
    horizontal_spacing=0.14
)

# --- subplot 1: max latency ---
fig.add_trace(go.Bar(
    name="Without TSN", x=streams, y=max_no_tsn,
    marker_color=COLORS["no_tsn"], text=[f"{v:.2f}" for v in max_no_tsn],
    textposition="outside"
), row=1, col=1)

fig.add_trace(go.Bar(
    name="With TSN", x=streams, y=max_with_tsn,
    marker_color=COLORS["with_tsn"], text=[f"{v:.3f}" for v in max_with_tsn],
    textposition="outside"
), row=1, col=1)

# deadline markers
for i, (stream, dl) in enumerate(zip(streams, deadlines)):
    fig.add_shape(type="line",
        x0=i - 0.4, x1=i + 0.4, y0=dl, y1=dl,
        line=dict(color=COLORS["deadline"], width=2, dash="dash"),
        row=1, col=1)

# invisible trace for deadline legend entry
fig.add_trace(go.Scatter(
    x=[None], y=[None], mode="lines", name="Deadline",
    line=dict(color=COLORS["deadline"], width=2, dash="dash")
), row=1, col=1)

# --- subplot 2: misses ---
fig.add_trace(go.Bar(
    name="Without TSN", x=streams, y=misses_no_tsn,
    marker_color=COLORS["no_tsn"], text=misses_no_tsn,
    textposition="outside", showlegend=False
), row=1, col=2)

fig.add_trace(go.Bar(
    name="With TSN", x=streams, y=misses_with_tsn,
    marker_color=COLORS["with_tsn"], text=misses_with_tsn,
    textposition="outside", showlegend=False
), row=1, col=2)

# ── Layout ────────────────────────────────────────────────────────────────────
fig.update_layout(
    title=dict(
        text="TSN Priority Scheduling — Freightliner Cascadia Zonal Network<br>"
             "<sup>Simulated 1000 ms | brake_cmd deadline = 2 ms | "
             "adas_flood deliberately overloads chassis link</sup>",
        x=0.5, xanchor="center", font_size=15
    ),
    barmode="group",
    plot_bgcolor="#1e1e2e",
    paper_bgcolor="#1e1e2e",
    font=dict(color="#cdd6f4", family="monospace"),
    legend=dict(bgcolor="#313244", bordercolor="#45475a", borderwidth=1),
    margin=dict(t=110, b=60),
    height=480, width=900,
)

fig.update_yaxes(gridcolor="#313244", row=1, col=1)
fig.update_yaxes(gridcolor="#313244", row=1, col=2)
fig.update_xaxes(tickfont_size=11)

# ── Export ────────────────────────────────────────────────────────────────────
fig.write_html("tsn_comparison.html")
fig.write_image("tsn_comparison.png", scale=2)
print("Saved: tsn_comparison.html  tsn_comparison.png")
