# Interactive Funnel Algorithm: Shortest Paths in Simple Polygons

An interactive application implementing the **Funnel Algorithm** (Lee & Preparata, 1984 / Chazelle, 1982) to find Euclidean shortest paths inside simple polygons.

---

## Features

- **Interactive Polygon Drawing**: Left-click to add vertices one by one; right-click to close the polygon. Real-time rubber banding and self-intersection validation.
- **Automatic Triangulation**: Triangulates the polygon instantly upon closing using the robust **Ear Clipping algorithm** ($O(n^2)$) without requiring user intervention.
- **Start and Target Declaration ($S$ & $T$)**: Click twice inside the polygon to define the starting point $S$ and destination $T$.
- **Dual Graph Corridor Search**: Uses BFS on the dual tree of the triangulation to extract the unique sleeve of triangles connecting $S$ and $T$ along with oriented portals.
- **Step-by-Step Funnel Algorithm**:
  - Each step is executed upon pressing **ENTER**.
  - Clearly visualizes the **Apex**, the **Left Chain**, the **Right Chain**, the **active Portal**, and the accumulated **Shortest Path**.
  - Provides a textual explanation of each geometric step (narrowing, tangent finding, or apex crossing).
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
| **Execute Next Step** | `ENTER` or `SPACE` |
| **Step Backward** | `Left Arrow` ($\leftarrow$) or `Backspace` |
| **Reset / New Polygon** | `R` |
| **Load Preset Corridor** | `1` (L-shape), `2` (U-shape), `3` (S-shape) |
| **Quit** | `ESC` or Close window |

---

## Algorithm Pipeline

```
[ User Draw Polygon ]
       │
       ▼ (Right-Click)
[ Simplicity Check & Ear Clipping Triangulation ]
       │
       ▼
[ User clicks S and T ]
       │
       ▼
[ Dual Graph Search (BFS Tree Path) ]
       │
       ▼
[ Extract Directed Portals (Left, Right) ]
       │
       ▼
[ Funnel Stepper (Step-by-step on ENTER) ]
 ├── Update Left Chain / Right Chain
 ├── Check Crossing & Move Apex
 └── Pull String to Target T
```

---

## Running the Unit Tests

The test suite validates polygon simplicity checks, ear-clipping triangulation, dual graph BFS, portal extraction, and funnel algorithm path accuracy on multiple convex and non-convex corridors:

```bash
.venv/bin/python -m unittest test_funnel.py
```

