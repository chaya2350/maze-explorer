# Living Maze Explorer

A random maze generator with an AI agent that visualizes how it searches for the exit — plus a human-play mode.

Built with Python and [pygame](https://www.pygame.org/).

## Features

- **Maze generation**: Recursive Backtracker algorithm, animated cell-by-cell as it carves the maze.
- **Search visualization**: watch **BFS**, **DFS**, or **A\*** explore the maze in real time, with a heatmap showing visit order (light blue = early, purple = late) and the frontier highlighted in yellow.
- **Agent walk**: once a path is found, an animated agent walks it step by step, with a short sound on arrival.
- **Human-play mode**: navigate the maze yourself with the arrow keys / WASD and compare your step count to the AI.
- **Algorithm comparison**: run BFS, DFS, and A\* on the same maze and see a side-by-side table of cells visited and path length.
- **Custom start/goal**: left-click to set the start, right-click to set the goal.
- **Difficulty levels**: Small, Medium, or Large maze sizes.

## Requirements

- Python 3
- [pygame](https://www.pygame.org/)

Install pygame:

```
pip install pygame
```

## Run

```
py maze.py
```

## Controls

| Key / Action              | Effect                                   |
|----------------------------|-------------------------------------------|
| `1` / `2` / `3`             | Select algorithm: BFS / DFS / A*           |
| `ENTER`                     | Start the search (or confirm on result screens) |
| `H`                          | Play the maze yourself                    |
| `C`                          | Compare BFS, DFS, and A* on the same maze |
| `F1` / `F2` / `F3`           | Difficulty: Small / Medium / Large        |
| Left-click / Right-click    | Set start / goal cell (in the menu)       |
| Arrow keys / `WASD`         | Move yourself in human-play mode          |
| `Up` / `Down`               | Adjust search/animation speed             |
| `R`                          | Generate a new maze                       |
| `ESC`                        | Quit                                       |
