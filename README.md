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
- **Direct Recording & Grid Plot Export**:
  - Automatically records cropped screenshots of your drawn polygon for each step (drawing area only, without UI header/footer bars).
  - When completing the final step (or pressing `E` / `P`), an interactive in-app modal prompts for the desired **number of columns (1 – 8)**.
  - Automatically arranges all recorded steps into a publication-quality `grid_plot.png` with step titles and a unified legend.

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
| **Step Backward** | `Left Arrow` ($\leftarrow$) or `Backspace` (pops undone step) |
| **Export Grid Plot** | `E` or `P` (prompts for columns: `1 - 8`, then saves `grid_plot.png`) |
| **Toggle Direct Recording** | `S` (captures drawing on each step, ON by default) |
| **Toggle Fullscreen** | `F` or `F11` (native 1:1 pixel rendering) |
| **Increase Resolution Preset** | `+` / `=` (720p → 900p → 1080p → 1440p → 4K) |
| **Decrease Resolution Preset** | `-` |
| **Reset / New Polygon** | `R` |
| **Quit** | `ESC` or Close window |

### Direct Recording & Column Selection on Export

Every step you perform on your drawn polygon is directly captured:
1. **Step 0**: Dual Tree & corridor path upon placing $S$ and $T$.
2. **Step 1**: Funnel initialized at Start $S$.
3. **Steps 2..N**: Dynamic portal updates, chain narrowing/widening, and boundary crossing visualization.
4. **Final Step**: Shortest path complete to Target $T$.

When the path completes (or when you press `E` / `P`), an in-app modal opens asking for the **number of columns in the plot**:
- Click any pill `[1]` through `[8]` or type `1`–`8` on your keyboard.
- Use `Up`/`Down` or `+`/`-` to increment/decrement.
- Press `ENTER` to confirm export, or `ESC` to cancel.

You can also specify a default column count via CLI:

```bash
# Set default export grid layout to 3 columns
.venv/bin/python main.py --cols 3

# Save direct recording screenshots to a custom folder
.venv/bin/python main.py --record screenshots/my_custom_run
```

The exported session folder contains:
- `step_00_dual_tree.png`: Pure drawing of the triangulation dual tree and corridor path.
- `step_01_funnel_init.png`: Initial funnel state at Start $S$.
- `step_XX_step.png`: Intermediate funnel states and portal updates.
- `step_XX_crossing.png`: Explicit crossing detection before apex moves.
- `step_XX_complete.png`: Complete shortest path to Target $T$.
- `grid_plot.png`: Publication-ready grid figure compiling all step drawings with titles, user-specified columns, and a comprehensive unified legend.

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

