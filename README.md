# Zonal E/E Architecture Analyzer + TSN Simulator

A two-stage Python tool that **designs** and **validates** zonal Ethernet architecture for Class 8 commercial trucks.

- **Stage 1** — quantifies the structural benefits of switching from legacy point-to-point wiring to a 4-zone Ethernet backbone (wire length, weight, cross-zone runs)
- **Stage 2** — simulates real-time traffic over that network and proves safety-critical signals meet their deadlines under three IEEE 802.1 TSN scheduling modes

> Built during an internship at **Daimler Truck Innovation Center India (DTICI)** on Freightliner and Western Star platforms.

---

## Key Results

### Stage 1 — Architecture Analysis (Freightliner Cascadia 126)

| Metric | Legacy | Zonal (4-zone) | Reduction |
|---|---|---|---|
| Cross-zone wire runs | 16 | 3 | **81.2% fewer** |
| Total wire length | 52.5 m | 24.3 m | **53.7% saved** |
| Estimated harness weight | 6.3 kg | 2.9 kg | **3.4 kg saved** |

### Stage 2 — TSN Simulation (brake command, 2 ms deadline)

| Mode | Max Latency | Misses | Result |
|---|---|---|---|
| No TSN (plain Ethernet) | 166.6 ms | 83 / 100 | ❌ FAIL |
| TSN Priority Scheduling | 0.167 ms | 0 / 100 | ✅ OK |
| TSN + Frame Preemption | 0.037 ms | 0 / 100 | ✅ OK |

**4500× latency improvement. Zero deadline misses under TSN with preemption.**

---

## What it does

```
YAML config (ECU layout + traffic streams)
        │
        ├── Stage 1: graph.py + metrics.py + optimizer.py
        │     └── wire length · weight · cross-zone runs · zone optimality
        │
        └── Stage 2: tsn/simulator.py (SimPy + NetworkX)
              └── FIFO → Priority → Preemption
                    └── latency · jitter · deadline miss count
                          └── PDF report (ReportLab)
```

---

## Vehicles Modelled

| Vehicle | ECUs | Class | TSN Config |
|---|---|---|---|
| Freightliner Cascadia 126 (2020) | 22 | Long-haul Class 8 | `cascadia_tsn_extension.yaml` |
| Western Star 49X (2021) | 17 | Vocational Class 8 | `westernstar_tsn_extension.yaml` |
| Mercedes-Benz Sprinter 519 CDI (2021) | 12 | Light commercial | *(Stage 1 only)* |

---

## Quick Start

```bash
git clone https://github.com/Rish-736/zonal-ee-analyzer
cd zonal-ee-analyzer
pip install -r requirements.txt

# Stage 1 — architecture analysis
python main.py --config configs/cascadia_126_2020.yaml --stage analyze

# Stage 2 — TSN simulation
python main.py --config configs/cascadia_tsn_extension.yaml --stage tsn

# Full pipeline — design + validate
python main.py --config configs/cascadia_tsn_extension.yaml --stage full

# Western Star
python main.py --config configs/westernstar_tsn_extension.yaml --stage tsn
```

---

## Repo Structure

```
zonal-ee-analyzer/
├── configs/
│   ├── cascadia_126_2020.yaml           # Freightliner Cascadia — ECU layout
│   ├── western_star_49x_2021.yaml       # Western Star 49X — ECU layout
│   ├── sprinter_van_2021.yaml           # Sprinter — ECU layout
│   ├── cascadia_tsn_extension.yaml      # Cascadia — TSN links + streams
│   └── westernstar_tsn_extension.yaml   # Western Star — TSN links + streams
├── src/
│   ├── parser.py                        # YAML → Python dict
│   ├── graph.py                         # NetworkX legacy + zonal graphs
│   ├── metrics.py                       # Wire length, weight, cross-zone runs
│   ├── visualize.py                     # Topology diagrams + bar charts
│   ├── optimizer.py                     # Zone boundary optimality (modularity)
│   ├── fleet_compare.py                 # Cross-vehicle comparison pipeline
│   ├── reviewer.py                      # AI review via Groq / Llama 3.3 70B
│   ├── build_pdf_report.py              # 18-page PDF report (ReportLab)
│   └── tsn/
│       ├── simulator.py                 # SimPy discrete-event TSN engine
│       └── pdf_section.py               # TSN section for the PDF report
├── main.py                              # Entry point — --stage flag
├── outputs/                             # Generated diagrams, charts, PDF
└── requirements.txt
```

---

## TSN Standards Implemented

| Standard | Name | What it models |
|---|---|---|
| IEEE 802.1Q | Bridges and Bridged Networks | Priority queue at each switch port |
| IEEE 802.1Qbu | Frame Preemption | High-priority frame interrupts mid-transmission |
| IEEE 802.1AS | Timing and Synchronization | Shared time reference (future work) |
| IEEE 802.1DG | TSN for Automotive Ethernet | Vehicle profile governing the above |

---

## Stack

`Python 3.11` · `SimPy` · `NetworkX` · `Matplotlib` · `ReportLab` · `Groq API (Llama 3.3 70B)` · `PyYAML` · `Pandas`

---

## Resume Bullet

> Built a two-stage Zonal E/E Architecture Analyzer + TSN Scheduler Simulator for Class 8 trucks (Freightliner Cascadia, Western Star 49X) using SimPy, NetworkX and ReportLab; modelled legacy-to-zonal topology transition (53.7% wire reduction, 3.4 kg saved) and validated deterministic IEEE 802.1Qbu frame preemption achieving 4500× brake-signal latency improvement with zero deadline misses under simulated ADAS traffic load.
