# Zonal E/E Architecture Analyzer

**A Python tool that models and compares legacy point-to-point vs. 4-zone Ethernet wiring architecture for commercial trucks — quantifying wire length reduction, harness weight savings, and zone boundary optimality across three real vehicles.**

Built as a personal R&D project alongside an internship at Daimler Truck Innovation Center India (DTICI), extending research on Class 8 truck E/E architecture redesign. All ECU data sourced from official public DTNA and Mercedes-Benz documentation.

> **The pipeline is vehicle-agnostic.** Any truck, van, bus, or passenger car can be modelled by writing a YAML config with its ECU list, zone assignments, and connection map. The analysis, diagrams, and PDF report generate automatically. See [Adding a New Vehicle](#adding-a-new-vehicle).

---

## Results

> Same ECUs. Same logical connections. Architecture change only.

### Freightliner Cascadia 126 — Primary Vehicle

| Metric | Legacy (Point-to-Point) | Zonal (4-Zone) | Reduction |
|---|---|---|---|
| Total wire length | 52.5 m | 24.3 m | **53.7% saved** |
| Cross-zone wire runs | 16 | 3 | **81.2% fewer** |
| Est. harness weight | 6.3 kg | 2.9 kg | **3.4 kg saved** |
| Zone efficiency score | — | — | **7.0%** |

### Fleet-Wide Comparison

| Vehicle | ECUs | Legacy Wire | Zonal Wire | Saved | Weight Saved | Zone Efficiency |
|---|---|---|---|---|---|---|
| Freightliner Cascadia 126 | 22 | 52.5 m | 24.3 m | **53.7%** | 3.4 kg | 7.0% |
| Western Star 49X | 17 | 56.5 m | 19.8 m | **65.0%** | 4.4 kg | -4.9% |
| Mercedes-Benz Sprinter 519 CDI | 12 | 20.5 m | 13.9 m | **32.2%** | 0.8 kg | 31.2% |

---

## Output Diagrams

### Legacy Point-to-Point Topology — Freightliner Cascadia 126
![Legacy topology](outputs/legacy_topology.png)

### Proposed 4-Zone Ethernet Architecture — Freightliner Cascadia 126
![Zonal topology](outputs/zonal_topology.png)

### Fleet-Wide Metric Comparison
![Comparison chart](outputs/comparison_chart.png)

---

## What This Tool Does

**1. Models two wiring architectures as graphs**
Reads a YAML truck config (ECUs, zones, connections, zone distances) and builds two NetworkX graphs — one for legacy point-to-point topology, one for 4-zone zonal topology. Edge weights represent estimated wire lengths based on published chassis dimensions.

**2. Calculates harness metrics**
Sums edge weights to compute total wire length. Counts cross-zone runs (edges > 0.5m). Estimates harness weight at 120 g/m bundled average. Computes percentage reductions between both topologies.

**3. Checks if zone boundaries are optimal**
Runs Greedy Modularity Community Detection (NetworkX) on a communication-only graph — ignoring physical location — to find the mathematically optimal zone groupings based purely on who talks to whom. Compares this to the human-defined physical zones using a modularity score. Flags ECUs whose communication pattern crosses zone boundaries.

**4. Runs across an entire fleet**
Executes the full pipeline for all three vehicle configs and outputs a cross-vehicle comparison table. Identifies scaling patterns — notably that zonal benefit depends more on physical ECU spread than total ECU count.

**5. Generates an AI engineering review**
Passes all computed metrics to Groq Llama 3.3 70B with a structured automotive engineering prompt. The AI generates a 7-section review referencing specific ECU names and computed numbers — not generic text.

**6. Produces an 18-page PDF comparative study report**
matplotlib generates 9 charts and 6 topology diagrams (legacy + zonal for all 3 vehicles). ReportLab assembles them with tables, AI review, methodology, and citations into a formatted PDF with a cover page, abbreviations guide, and page numbers.

---

## Key Finding

The **Zone Efficiency Score** is the most technically interesting result. It measures how closely the human-drawn physical zones match what a graph algorithm would compute from communication patterns alone.

All three vehicles score low (7.0%, -4.9%, 31.2%). This is not a mistake — it is a genuine engineering insight:

- **Physical zones** minimise local wire length (ECUs close to their Zone Controller)
- **Communication-optimal zones** minimise cross-zone message frequency (heavily-communicating ECUs in the same zone)
- **These two criteria produce almost completely different groupings** on a real truck

This tension is the core design challenge in zonal E/E architecture. It is why ICU (dashboard) ends up in the same algorithm-optimal cluster as MCM (engine) — they talk constantly despite being on opposite ends of the truck. The industry currently resolves this through engineering judgment. This tool quantifies the gap for the first time in open source.

---

## Adding a New Vehicle

The entire pipeline is driven by the YAML config file. To model any new vehicle — a different truck, a bus, a passenger car, an EV platform — you only need to create one file. No code changes required.

### What you need to know about the vehicle

```
1. ECU list        — what electronic control units exist on the vehicle
2. Zone assignment — which physical region each ECU is mounted in
3. Connections     — which pairs of ECUs must communicate, and what data flows
4. Chassis size    — approximate distances between zones in meters
```

### Where to find this data

For commercial vehicles, the following public sources have been used successfully:

| Source type | Example | What it gives you |
|---|---|---|
| OEM J1939 service bulletins | DTNA SS-1033423 (NHTSA database) | Full ECU list with source addresses |
| OEM bodybuilder manuals | Western Star Bodybuilder Manual | Zone layout and ECU placement |
| OEM diagnostic documentation | Mercedes-Benz XENTRY public docs | ECU names and network topology |
| SAE J1939 standard | SAE International | Standardised ECU categories for heavy vehicles |
| Academic papers | Park et al., Sensors 2024 | Representative ECU sets with zone assignments |

For vehicles where OEM data is unavailable, a representative model built from public sources is a valid and academically accepted approach — see the Methodology Notes section.

### YAML config format

Create `configs/your_vehicle.yaml` following this structure:

```yaml
metadata:
  truck_model: "Your Vehicle Name (Year)"
  total_ecus: 18          # count of ECUs
  source: "Data source citation"
  notes: "Any relevant notes"

# Estimated distances in meters between zone centroids
# Based on the vehicle's published chassis dimensions
zone_distances:
  ptz_to_chz: 2.5         # powertrain to chassis zone
  chz_to_cbz: 2.0         # chassis to cab zone
  cbz_to_frz: 1.5         # cab to front zone
  ptz_to_cbz: 4.5         # powertrain to cab (used for cross-zone edges)
  ptz_to_frz: 6.0         # longest run: powertrain to front
  chz_to_frz: 3.5
  cbz_to_chz: 2.0

zones:
  - name: "Powertrain Zone"
    id: PTZ
    location: "Engine compartment"
    zone_controller: "ZC-PT"
    ecus:
      - id: ECM                          # short identifier used in connections
        name: "Engine Control Module"
        j1939_sa: 0                      # J1939 source address (0 if unknown)
        function: "Controls engine"
        local_wire_length_m: 0.5         # stub wire length in zonal architecture

      # add more ECUs here...

  - name: "Chassis Zone"
    id: CHZ
    location: "Frame rails"
    zone_controller: "ZC-CH"
    ecus:
      - id: ABS
        name: "ABS Controller"
        j1939_sa: 11
        function: "Anti-lock braking"
        local_wire_length_m: 1.0

  - name: "Cab Zone"
    id: CBZ
    location: "Driver cab interior"
    zone_controller: "ZC-CAB"
    ecus:
      - id: ICU
        name: "Instrument Cluster Unit"
        j1939_sa: 23
        function: "Driver display"
        local_wire_length_m: 0.5

  - name: "Front Zone"
    id: FRZ
    location: "Front fascia"
    zone_controller: "ZC-FR"
    ecus:
      - id: CAM
        name: "Forward Camera"
        j1939_sa: 128
        function: "Collision avoidance"
        local_wire_length_m: 0.6

connections:
  - {from: ECM,  to: ICU, signal: "Engine RPM and temperature to dashboard"}
  - {from: ABS,  to: ICU, signal: "ABS warning light"}
  - {from: ABS,  to: ECM, signal: "Wheel speed for traction control"}
  - {from: CAM,  to: ICU, signal: "Lane departure alert"}
  # add more connections here...
```

### Run the analysis on your new vehicle

```bash
# Single vehicle analysis
python main.py configs/your_vehicle.yaml

# Add it to the fleet comparison
# Edit the CONFIGS list in src/fleet_compare.py to include your file
# Then run:
python src/fleet_compare.py

# Full PDF report including your vehicle
python src/build_pdf_report.py
```

### Minimum viable config

At minimum you need: at least 2 zones, at least 5 ECUs, at least 3 connections, and realistic zone distances. The tool will run with partial data — you will get results, but accuracy improves with more complete connection maps.

---

## How to Run

**1. Clone the repository**
```bash
git clone https://github.com/Rish-736/zonal-ee-analyzer.git
cd zonal-ee-analyzer
```

**2. Install dependencies**
```bash
pip install -r requirements.txt
```

**3. Run the basic pipeline** (graphs + metrics + diagrams)
```bash
python main.py
```

**4. Run zone boundary optimality analysis**
```bash
python src/optimizer.py
```

**5. Run fleet-wide comparison across all 3 vehicles**
```bash
python src/fleet_compare.py
```

**6. Generate the full 18-page PDF report** (requires Groq API key in `src/reviewer.py`)
```bash
python src/build_pdf_report.py
```
Get a free Groq API key at [console.groq.com](https://console.groq.com) — no credit card required.

---

## Repository Structure

```
zonal-ee-analyzer/
├── configs/
│   ├── cascadia_126_2020.yaml        ← Freightliner Cascadia 126 — 22 ECUs, 25 connections
│   ├── western_star_49x_2021.yaml    ← Western Star 49X — 17 ECUs, 22 connections
│   └── sprinter_van_2021.yaml        ← MB Sprinter 519 CDI — 12 ECUs, 13 connections
├── src/
│   ├── parser.py                     ← Reads YAML config → Python dictionary
│   ├── graph.py                      ← Builds legacy and zonal NetworkX graphs
│   ├── metrics.py                    ← Calculates wire length, weight, cross-zone runs
│   ├── visualize.py                  ← Draws topology diagrams and comparison chart
│   ├── optimizer.py                  ← Greedy modularity community detection
│   ├── fleet_compare.py              ← Full pipeline across all vehicle configs
│   ├── reviewer.py                   ← Groq Llama 3.3 70B AI review (add API key here)
│   └── build_pdf_report.py           ← 18-page PDF comparative study report generator
├── outputs/                          ← Generated PNGs and PDF (auto-created on run)
├── main.py                           ← Entry point: parser → graph → metrics → visualize
├── requirements.txt
└── README.md
```

---

## Tech Stack

| Library | Purpose |
|---|---|
| `networkx` | Graph construction, edge weight analysis, greedy modularity community detection |
| `matplotlib` | Topology diagrams (6 total) and comparison charts (3 total) |
| `pyyaml` | YAML config file parsing |
| `tabulate` | Formatted terminal output tables |
| `reportlab` | 18-page PDF assembly with tables, images, and styled text |
| `groq` | Groq API client for Llama 3.3 70B AI engineering review |
| `numpy` | Array operations for chart bar positioning |

All free and open-source. No paid licenses required.

---

## Vehicles Modelled

**Freightliner Cascadia 126 (2020)** — Class 8 long-haul truck, 22 ECUs
> PTZ: MCM, CPC, ACM, TCM | CHZ: ABS, ECAS, TPMS, SAM-Chassis | CBZ: ICU, CGW, SAM-Cab, FCU, SRS, MSF, ParkSmart, DCMD, DCMP, TCO | FRZ: MPC, OnGuard, SAS, CTP

**Western Star 49X (2021)** — Class 8 vocational truck, 17 ECUs
> Same DTNA platform as Cascadia. Adds PTO controller and tandem axle lock controller. Removes sleeper ECUs. Shorter chassis with more physically distributed ECU layout.

**Mercedes-Benz Sprinter 519 CDI (2021)** — Light commercial van, 12 ECUs
> Included for scale comparison. Demonstrates that zonal architecture still saves 32.2% wire on smaller vehicles, but the hardware overhead of 4 zone controllers is proportionally higher at low ECU counts.

---

## Data Sources

| Source | Used for |
|---|---|
| **DTNA SS-1033423** — J-1939 Fault Code Source Address Descriptions. Daimler Trucks North America. NHTSA public database. | Complete Cascadia ECU list with J1939 source addresses |
| **DTNA STI-503** — NGC sSAM, VPDM & BCA Wall Chart. Rev. Q, March 2020. | Physical ECU location confirmation via fuse/relay assignments |
| **Western Star Bodybuilder Manual Rev 3.1** | Western Star 49X ECU configuration |
| **Mercedes-Benz XENTRY public diagnostic documentation** | Sprinter 519 CDI ECU configuration |
| **Park C, Cui C, Park S.** Sensors 2024;24(10):3248. DOI: 10.3390/s24103248 | Academic validation of representative-model methodology |
| **SAE J1939** — Serial Control and Communications Heavy Duty Vehicle Network | Protocol reference for ECU source address assignments |

---

## Methodology Notes

- Analysis covers signal and data wires only — power distribution harness excluded
- Harness weight uses 120 g/m bundled average for signal-wire harnesses (conservative estimate)
- Zone distances are point-to-point approximations between zone centroids based on published chassis dimensions
- Static ECU configuration — optional equipment and regional variant builds not modelled
- Zone efficiency score = human modularity score ÷ algorithm-optimal modularity score × 100
- The representative-model approach is academically validated by Park et al. (2024), who used the same methodology in a peer-reviewed journal publication

---

## Context

Built alongside internship research at **Daimler Truck Innovation Center India (DTICI)**, where related work included KiCad door harness schematics (DCM architecture for Freightliner/Western Star), Zonal Ethernet Architecture research for Class 8 trucks (TSN, SOME/IP, J1939 bridging), and the Structural Printed Wiring Harness (SPWH) feasibility project under DTNA.

---

## Resume Bullet

*Built Zonal E/E Architecture Analyzer in Python — models legacy vs. 4-zone Ethernet topology for 3 commercial vehicles (22/17/12 ECUs) using NetworkX graph analysis; quantifies 53–65% wire reduction and applies greedy modularity community detection to evaluate zone boundary optimality; auto-generates 18-page PDF report with AI review (Groq Llama 3.3 70B). Pipeline is vehicle-agnostic — extensible to any platform via YAML config.*

---

## License

MIT — free to use, modify, and extend. Attribution appreciated.
