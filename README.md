# Interactive Funnel Algorithm: Shortest Paths in Simple Polygons

An interactive application implementing the **Funnel Algorithm** (Lee & Preparata, 1984 / Chazelle, 1982) to find Euclidean shortest paths inside simple polygons.

---

## Features

- **Interactive Polygon Drawing**: Left-click to add vertices one by one; right-click to close the polygon. Real-time rubber banding and self-intersection validation.
- **Automatic Triangulation**: Triangulates the polygon instantly upon closing using the robust **Ear Clipping algorithm** ($O(n^2)$) without requiring user intervention.
- **Start and Target Declaration ($S$ & $T$)**: Click twice inside the polygon to define the starting point $S$ and destination $T$.
- **Dedicated Dual Tree Phase**: Immediately after selecting $S$ and $T$, the application renders the entire **dual tree** of the triangulation (centroids and shared-edge dual links) and highlights the unique tree path connecting $S$ to $T$.
- **Step-by-Step Funnel Algorithm**:
  - Each step is executed upon pressing **ENTER**.
  - **Crossing Detection before Apex Move**: Before the apex jumps around a corner, the app explicitly highlights that a sightline from the apex has crossed the opposite boundary (showing the crossed line and the reflex corner), explaining why the apex must advance.
  - Clearly visualizes the **Apex**, the **Left Chain**, the **Right Chain**, the **active Portal**, and the accumulated **Shortest Path**.
  - Allows stepping **forward** (`ENTER` / `SPACE`) or **backward** (`←` / `Backspace`).
- **Quick Presets**: Press `1`, `2`, or `3` to instantly load demo polygons (L-shaped, U-shaped obstacle corridor, and S-shaped maze).

---

## Installation & Setup

A virtual environment (`.venv`) is set up in this repository.

To activate the virtual environment and run the application:

```bash
# Activate venv
source .venv/bin/activate

# Run interactive Pygame app
python main.py
```

Or run directly using the venv Python binary:

```bash
.venv/bin/python main.py
```

*(An alternative Matplotlib interactive script is also provided via `.venv/bin/python interactive_matplotlib.py`)*

---

## Controls & Usage

| Action | Control |
|---|---|
| **Add Vertex** | **Left-Click** (during Phase 1) |
| **Close Polygon** | **Right-Click** |
| **Undo Last Vertex** | `U` or `Backspace` |
| **Place Start Point (S)** | **Left-Click** inside the polygon (Phase 2) |
| **Place Target Point (T)** | **Left-Click** inside the polygon (Phase 2) |
| **Show Funnel (after Dual Tree)** | `ENTER` or `SPACE` |
| **Execute Next Step** | `ENTER` or `SPACE` |
| **Step Backward** | `Left Arrow` ($\leftarrow$) or `Backspace` |
| **Export All Steps Grid Plot** | `P` or `G` (exports cropped step screenshots & `grid_plot.png`) |
| **Toggle Live Step Recording** | `S` (captures drawing on each forward step) |
| **Toggle Fullscreen** | `F` or `F11` (native 1:1 pixel rendering) |
| **Increase Resolution Preset** | `+` / `=` (720p → 900p → 1080p → 1440p → 4K) |
| **Decrease Resolution Preset** | `-` |
| **Reset / New Polygon** | `R` |
| **Load Preset Corridor** | `1` (L-shape), `2` (U-shape), `3` (S-shape) |
| **Quit** | `ESC` or Close window |

### Step Screenshots & Grid Plot Export

You can record every step or export a unified step-by-step summary grid plot (drawing area only, without UI header/footer bars):

```bash
# 1. Start with live step recording enabled
.venv/bin/python main.py --record screenshots/my_run

# 2. Automatically load a preset, export all steps, and generate grid_plot.png
.venv/bin/python main.py --export-grid 1 --screenshots screenshots/preset1
.venv/bin/python main.py --export-grid 2 --screenshots screenshots/preset2
.venv/bin/python main.py --export-grid 3 --screenshots screenshots/preset3

# 3. Interactive shortcut:
# Press 'P' at any time while running to export all steps and the grid plot!
```

The exported folder contains:
- `step_00_dual_tree.png`: Pure drawing of the triangulation dual tree and corridor path.
- `step_01_funnel_init.png`: Initial funnel state at Start $S$.
- `step_XX_step.png`: Intermediate funnel states and portal updates.
- `step_XX_crossing.png`: Explicit crossing detection before apex moves.
- `step_XX_complete.png`: Complete shortest path to Target $T$.
- `grid_plot.png`: Publication-ready grid figure compiling all step drawings with titles and a comprehensive unified legend.

### High Resolution & Launch Options

You can specify resolution at startup:

```bash
# Default is crisp 1080p (1920x1080)
.venv/bin/python main.py

# Launch directly in 1440p (2K) or 4K UHD
.venv/bin/python main.py --res 1440p
.venv/bin/python main.py --res 4k

# Launch in native fullscreen
.venv/bin/python main.py --fullscreen

# Match full desktop monitor resolution
.venv/bin/python main.py --res max
```

---

## Algorithm Pipeline

```
[ User Draws Polygon ]
       │
       ▼ (Right-Click)
[ Ear Clipping Triangulation ]
       │
       ▼
[ User clicks S and T ]
       │
       ▼
[ 1. Display Dual Tree & Corridor Path ] ── (Press ENTER)
       │
       ▼
[ 2. Initialize Funnel at S ]
       │
       ▼ (Press ENTER)
[ 3. Funnel Stepping Loop ]
       ├── Boundary Narrowing / Widening
       ├── ⚠ Crossing Detected! (Shows candidate line crossing boundary)
       ├── Apex Moves to Corner (Shortest path extended)
       └── Final connection to Target T
```

---

## Running the Unit Tests

The test suite validates polygon simplicity checks, ear-clipping triangulation, dual graph BFS, portal extraction, and funnel algorithm path accuracy on multiple convex and non-convex corridors:

```bash
.venv/bin/python -m unittest test_funnel.py
```

