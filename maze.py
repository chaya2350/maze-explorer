import pygame
import random
import sys
import heapq
import math
import array
from collections import deque

# --- constants ---
CELL   = 20            # cell size in pixels
COLS   = 25            # default number of columns (Medium)
ROWS   = 19            # default number of rows (Medium)

DIFFICULTIES = {
    pygame.K_F1: ("Small", 11, 9),
    pygame.K_F2: ("Medium", 25, 19),
    pygame.K_F3: ("Large", 39, 29),
}

WALL   = 1
PATH   = 0

GRID_W = COLS * 2 + 1
GRID_H = ROWS * 2 + 1

PANEL_H = 60
FPS = 60
GEN_STEPS_PER_FRAME = 15  # how many carve steps to animate per frame during maze generation

# colors (RGB)
COLOR_BG        = (18, 18, 26)
COLOR_WALL      = (70, 80, 120)
COLOR_PATH      = (235, 235, 240)
COLOR_START     = (80, 200, 120)
COLOR_GOAL      = (230, 120, 120)
COLOR_VISITED_NEAR = (110, 200, 255)  # heatmap color for cells visited early
COLOR_VISITED_FAR  = (120, 60, 200)   # heatmap color for cells visited late
COLOR_FRONTIER  = (255, 210, 90)
COLOR_FINALPATH = (255, 200, 40)
COLOR_AGENT     = (240, 80, 200)
COLOR_HUMAN     = (90, 220, 220)
COLOR_TRAIL     = (60, 90, 70)
COLOR_TEXT      = (240, 240, 245)
COLOR_PANEL     = (30, 30, 42)

pygame.init()
FONT       = pygame.font.SysFont("arial", 22)
FONT_SMALL = pygame.font.SysFont("arial", 16)
FONT_MONO  = pygame.font.SysFont("consolas", 20)
FONT_BIG   = pygame.font.SysFont("arial", 34, bold=True)

screen = pygame.display.set_mode((GRID_W * CELL, GRID_H * CELL + PANEL_H))
pygame.display.set_caption("Maze Explorer — agent finding the way")
clock = pygame.time.Clock()


def resize_window(cols, rows):
    """Resize the game window to fit a maze of the given size, returns (height, width) of the grid."""
    global screen
    grid_w, grid_h = cols * 2 + 1, rows * 2 + 1
    screen = pygame.display.set_mode((grid_w * CELL, grid_h * CELL + PANEL_H))
    return grid_h, grid_w


def make_beep(freq, duration_ms, volume=0.5, sample_rate=44100):
    """Synthesize a short fading sine-wave beep, no sound file needed."""
    n_samples = int(sample_rate * duration_ms / 1000)
    amplitude = int(32767 * volume)
    buf = array.array("h")
    for i in range(n_samples):
        fade = 1.0 - (i / n_samples)
        sample = int(amplitude * fade * math.sin(2 * math.pi * freq * i / sample_rate))
        buf.append(sample)
        buf.append(sample)
    return pygame.mixer.Sound(buffer=buf.tobytes())


try:
    pygame.mixer.init()
    SOUND_GOAL = make_beep(880, 220)
except pygame.error:
    SOUND_GOAL = None


def play_goal_sound():
    if SOUND_GOAL:
        SOUND_GOAL.play()

# --- maze generator: Recursive Backtracker ---
def generate_maze_steps(cols, rows):
    """Generator: yields (grid, height, width, done) after every carve step, for animation."""
    width = cols * 2 + 1
    height = rows * 2 + 1
    grid = [[WALL] * width for _ in range(height)]

    grid[1][1] = PATH
    stack = [(1, 1)]
    yield grid, height, width, False

    while stack:
        x, y = stack[-1]
        directions = [(-2, 0), (2, 0), (0, -2), (0, 2)]
        random.shuffle(directions)
        moved = False
        for dx, dy in directions:
            nx, ny = x + dx, y + dy
            if 0 <= nx < height and 0 <= ny < width and grid[nx][ny] == WALL:
                # carve the wall between the two cells and the cell itself
                grid[x + dx // 2][y + dy // 2] = PATH
                grid[nx][ny] = PATH
                stack.append((nx, ny))
                moved = True
                break
        if not moved:
            stack.pop()
        yield grid, height, width, (len(stack) == 0)


def neighbors(grid, height, width, pos):
    x, y = pos
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        nx, ny = x + dx, y + dy
        if 0 <= nx < height and 0 <= ny < width and grid[nx][ny] == PATH:
            yield (nx, ny)


def reconstruct_path(came_from, start, goal):
    if goal != start and goal not in came_from:
        return None
    path = [goal]
    cur = goal
    while cur != start:
        cur = came_from[cur]
        path.append(cur)
    path.reverse()
    return path


# --- search algorithms: each is a generator that advances one step at a time for animation ---
def bfs_search(grid, height, width, start, goal):
    frontier = deque([start])
    came_from = {start: None}
    visited_order = [start]
    while frontier:
        current = frontier.popleft()
        if current == goal:
            path = reconstruct_path(came_from, start, goal)
            yield {"done": True, "path": path, "visited": visited_order,
                   "current": current, "frontier": list(frontier)}
            return
        for nxt in neighbors(grid, height, width, current):
            if nxt not in came_from:
                came_from[nxt] = current
                frontier.append(nxt)
                visited_order.append(nxt)
        yield {"done": False, "path": None, "visited": visited_order,
               "current": current, "frontier": list(frontier)}
    yield {"done": True, "path": None, "visited": visited_order, "current": None, "frontier": []}


def dfs_search(grid, height, width, start, goal):
    frontier = [start]
    came_from = {start: None}
    visited_set = {start}
    visited_order = [start]
    while frontier:
        current = frontier.pop()
        if current == goal:
            path = reconstruct_path(came_from, start, goal)
            yield {"done": True, "path": path, "visited": visited_order,
                   "current": current, "frontier": list(frontier)}
            return
        for nxt in neighbors(grid, height, width, current):
            if nxt not in visited_set:
                visited_set.add(nxt)
                came_from[nxt] = current
                frontier.append(nxt)
                visited_order.append(nxt)
        yield {"done": False, "path": None, "visited": visited_order,
               "current": current, "frontier": list(frontier)}
    yield {"done": True, "path": None, "visited": visited_order, "current": None, "frontier": []}


def astar_search(grid, height, width, start, goal):
    def h(a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    counter = 0
    open_heap = [(h(start, goal), counter, start)]
    came_from = {}
    g_score = {start: 0}
    in_open = {start}
    visited_order = [start]
    while open_heap:
        _, _, current = heapq.heappop(open_heap)
        in_open.discard(current)
        if current == goal:
            path = reconstruct_path(came_from, start, goal)
            yield {"done": True, "path": path, "visited": visited_order,
                   "current": current, "frontier": [item[2] for item in open_heap]}
            return
        for nxt in neighbors(grid, height, width, current):
            tentative = g_score[current] + 1
            if tentative < g_score.get(nxt, float("inf")):
                came_from[nxt] = current
                g_score[nxt] = tentative
                counter += 1
                heapq.heappush(open_heap, (tentative + h(nxt, goal), counter, nxt))
                if nxt not in in_open:
                    in_open.add(nxt)
                    visited_order.append(nxt)
        yield {"done": False, "path": None, "visited": visited_order,
               "current": current, "frontier": [item[2] for item in open_heap]}
    yield {"done": True, "path": None, "visited": visited_order, "current": None, "frontier": []}


ALGO_LIST = [("BFS", bfs_search), ("DFS", dfs_search), ("A*", astar_search)]

ALGOS = {
    pygame.K_1: ALGO_LIST[0],
    pygame.K_2: ALGO_LIST[1],
    pygame.K_3: ALGO_LIST[2],
    pygame.K_KP1: ALGO_LIST[0],
    pygame.K_KP2: ALGO_LIST[1],
    pygame.K_KP3: ALGO_LIST[2],
}


def run_to_completion(algo_func, grid, height, width, start, goal):
    last_step = None
    for step in algo_func(grid, height, width, start, goal):
        last_step = step
    return last_step


# --- drawing ---
def draw_menu(grid, height, width, algo_name, start, goal, difficulty_name, last_result=None):
    draw_maze(grid, height, width, [], [], None, None, None, start, goal)

    lines = [
        "Choose a search algorithm:",
        "[1] BFS      [2] DFS      [3] A*",
        f"Selected algorithm: {algo_name}",
        f"Difficulty: {difficulty_name}    [F1] Small  [F2] Medium  [F3] Large",
        "Left-click: set start    Right-click: set goal",
        "",
        "ENTER — start search      H — play it yourself      C — compare all",
        "R — new maze      ESC — quit",
    ]
    if last_result:
        lines.append("")
        lines.append(last_result)

    panel_height = 60 + len(lines) * 32
    overlay = pygame.Surface((screen.get_width(), panel_height), pygame.SRCALPHA)
    overlay.fill((15, 15, 20, 215))
    screen.blit(overlay, (0, 20))

    title = FONT_BIG.render("Living Maze Explorer", True, COLOR_TEXT)
    screen.blit(title, title.get_rect(center=(screen.get_width() // 2, 60)))

    y = 60 + 48
    for line in lines:
        surf = FONT.render(line, True, COLOR_TEXT)
        screen.blit(surf, surf.get_rect(center=(screen.get_width() // 2, y)))
        y += 32


def draw_comparison(grid, height, width, start, goal, results):
    draw_maze(grid, height, width, [], [], None, None, None, start, goal)

    rows = []
    for name, step in results:
        path = step["path"]
        visited_count = len(step["visited"])
        path_text = f"{len(path)} cells" if path else "no path"
        rows.append(f"{name:<4} visited: {visited_count:>4} cells   path: {path_text}")

    lines = ["Algorithm Comparison"] + rows + ["", "ENTER — back to menu      R — new maze"]

    panel_height = 60 + len(lines) * 32
    overlay = pygame.Surface((screen.get_width(), panel_height), pygame.SRCALPHA)
    overlay.fill((15, 15, 20, 215))
    screen.blit(overlay, (0, 20))

    y = 60
    for i, line in enumerate(lines):
        font = FONT_BIG if i == 0 else (FONT_MONO if line in rows else FONT)
        surf = font.render(line, True, COLOR_TEXT)
        screen.blit(surf, surf.get_rect(center=(screen.get_width() // 2, y)))
        y += 48 if i == 0 else 32


def draw_panel(text):
    rect = pygame.Rect(0, screen.get_height() - PANEL_H, screen.get_width(), PANEL_H)
    pygame.draw.rect(screen, COLOR_PANEL, rect)
    surf = FONT_SMALL.render(text, True, COLOR_TEXT)
    screen.blit(surf, (10, rect.top + PANEL_H // 2 - surf.get_height() // 2))


def lerp_color(c1, c2, t):
    return (
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t),
    )


def draw_maze(grid, height, width, visited, frontier, current, path, agent_pos, start, goal, trail=None, trail_color=COLOR_TRAIL):
    screen.fill(COLOR_BG)
    # heatmap: color visited cells by how early/late they were reached during the search
    visited_index = {p: i for i, p in enumerate(visited)}
    last_index = max(1, len(visited) - 1)
    frontier_set = set(frontier)
    path_set = set(path) if path else set()
    trail_set = set(trail) if trail else set()

    for x in range(height):
        for y in range(width):
            cell = grid[x][y]
            color = COLOR_WALL
            if cell == PATH:
                color = COLOR_PATH
                if (x, y) in path_set:
                    color = COLOR_FINALPATH
                elif (x, y) in frontier_set:
                    color = COLOR_FRONTIER
                elif (x, y) in visited_index:
                    t = visited_index[(x, y)] / last_index
                    color = lerp_color(COLOR_VISITED_NEAR, COLOR_VISITED_FAR, t)
                elif (x, y) in trail_set:
                    color = trail_color
            pygame.draw.rect(screen, color, (y * CELL, x * CELL, CELL, CELL))

    pygame.draw.rect(screen, COLOR_START, (start[1] * CELL, start[0] * CELL, CELL, CELL))
    pygame.draw.rect(screen, COLOR_GOAL, (goal[1] * CELL, goal[0] * CELL, CELL, CELL))

    if current is not None:
        cx, cy = current
        pygame.draw.rect(screen, (255, 255, 255), (cy * CELL, cx * CELL, CELL, CELL), 2)

    if agent_pos is not None:
        ax, ay = agent_pos
        center = (ay * CELL + CELL // 2, ax * CELL + CELL // 2)
        pygame.draw.circle(screen, COLOR_AGENT, center, CELL // 2 - 2)


HUMAN_MOVES = {
    pygame.K_UP: (-1, 0), pygame.K_w: (-1, 0),
    pygame.K_DOWN: (1, 0), pygame.K_s: (1, 0),
    pygame.K_LEFT: (0, -1), pygame.K_a: (0, -1),
    pygame.K_RIGHT: (0, 1), pygame.K_d: (0, 1),
}


# --- main game loop ---
def main():
    steps_per_frame = 4  # search speed, can be changed with up/down arrows
    difficulty_name, cols, rows = "Medium", COLS, ROWS

    gen_gen = generate_maze_steps(cols, rows)
    grid, height, width, gen_done = next(gen_gen)
    start, goal = (1, 1), (height - 2, width - 2)
    algo_key = pygame.K_1
    state = "generating"

    search_gen = None
    visited, frontier, current, path = [], [], None, None
    agent_path, agent_index, agent_timer = None, 0, 0
    human_pos, human_trail, human_steps = None, [], 0
    last_result = None  # text describing the most recent finished run, shown in the menu
    comparison_results = []

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and state == "menu":
                mx, my = event.pos
                if my < height * CELL:
                    row, col = my // CELL, mx // CELL
                    if 0 <= row < height and 0 <= col < width and grid[row][col] == PATH:
                        if event.button == 1 and (row, col) != goal:
                            start = (row, col)
                        elif event.button == 3 and (row, col) != start:
                            goal = (row, col)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_r:
                    gen_gen = generate_maze_steps(cols, rows)
                    grid, height, width, gen_done = next(gen_gen)
                    start, goal = (1, 1), (height - 2, width - 2)
                    state = "generating"
                    search_gen = None
                    visited, frontier, current, path = [], [], None, None
                    agent_path, agent_index = None, 0
                    human_pos, human_trail, human_steps = None, [], 0
                elif state == "menu" and event.key in DIFFICULTIES:
                    difficulty_name, cols, rows = DIFFICULTIES[event.key]
                    resize_window(cols, rows)
                    gen_gen = generate_maze_steps(cols, rows)
                    grid, height, width, gen_done = next(gen_gen)
                    start, goal = (1, 1), (height - 2, width - 2)
                    state = "generating"
                elif state == "menu" and event.key in ALGOS:
                    algo_key = event.key
                elif state == "menu" and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    _, algo_func = ALGOS[algo_key]
                    search_gen = algo_func(grid, height, width, start, goal)
                    visited, frontier, current, path = [], [], None, None
                    state = "searching"
                elif state == "menu" and event.key == pygame.K_h:
                    human_pos, human_trail, human_steps = start, [start], 0
                    state = "human"
                elif state == "menu" and event.key == pygame.K_c:
                    comparison_results = [
                        (name, run_to_completion(func, grid, height, width, start, goal))
                        for name, func in ALGO_LIST
                    ]
                    state = "comparing"
                elif state == "comparing" and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    state = "menu"
                elif state == "done" and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    algo_name, _ = ALGOS[algo_key]
                    last_result = f"{algo_name}: {len(path)} cells" if path else f"{algo_name}: no path"
                    state = "menu"
                    search_gen = None
                elif state == "human_done" and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    last_result = f"You: {human_steps} steps"
                    state = "menu"
                elif state == "human" and event.key in HUMAN_MOVES:
                    dx, dy = HUMAN_MOVES[event.key]
                    nx, ny = human_pos[0] + dx, human_pos[1] + dy
                    if 0 <= nx < height and 0 <= ny < width and grid[nx][ny] == PATH:
                        human_pos = (nx, ny)
                        human_steps += 1
                        human_trail.append(human_pos)
                        if human_pos == goal:
                            state = "human_done"
                            play_goal_sound()
                elif state in ("searching", "animating", "done") and event.key == pygame.K_UP:
                    steps_per_frame = min(steps_per_frame * 2, 256)
                elif state in ("searching", "animating", "done") and event.key == pygame.K_DOWN:
                    steps_per_frame = max(steps_per_frame // 2, 1)

        algo_name, _ = ALGOS[algo_key]

        if state == "generating":
            for _ in range(GEN_STEPS_PER_FRAME):
                nxt = next(gen_gen, None)
                if nxt is None:
                    break
                grid, height, width, gen_done = nxt
                if gen_done:
                    start, goal = (1, 1), (height - 2, width - 2)
                    state = "menu"
                    break

            draw_maze(grid, height, width, [], [], None, None, None, start, goal)
            draw_panel("Carving the maze...")

        elif state == "menu":
            draw_menu(grid, height, width, algo_name, start, goal, difficulty_name, last_result)

        elif state == "comparing":
            draw_comparison(grid, height, width, start, goal, comparison_results)

        elif state == "searching":
            for _ in range(steps_per_frame):
                step = next(search_gen, None)
                if step is None:
                    break
                visited = step["visited"]
                frontier = step["frontier"]
                current = step["current"]
                if step["done"]:
                    path = step["path"]
                    if path:
                        agent_path, agent_index, agent_timer = path, 0, 0
                        state = "animating"
                    else:
                        state = "done"
                    break

            draw_maze(grid, height, width, visited, frontier, current, path, None, start, goal)
            draw_panel(f"{algo_name} searching... cells checked: {len(visited)}   [Up/Down] speed  [R] new maze")

        elif state == "animating":
            agent_timer += 1
            if agent_timer >= 6:
                agent_timer = 0
                if agent_index < len(agent_path) - 1:
                    agent_index += 1
                else:
                    state = "done"
                    play_goal_sound()

            draw_maze(grid, height, width, visited, frontier, None, path, agent_path[agent_index], start, goal)
            draw_panel(f"{algo_name}: agent walking to the exit... step {agent_index + 1}/{len(agent_path)}   [R] new maze")

        elif state == "done":
            agent_pos = agent_path[-1] if agent_path else None
            draw_maze(grid, height, width, visited, frontier, None, path, agent_pos, start, goal)
            if path:
                msg = f"{algo_name}: reached the goal! Path length: {len(path)} cells"
            else:
                msg = f"{algo_name}: no path found"
            draw_panel(msg + "   [ENTER] menu   [R] new maze")

        elif state == "human":
            draw_maze(grid, height, width, [], [], None, None, human_pos, start, goal, trail=human_trail)
            draw_panel(f"Your turn! Steps so far: {human_steps}   [Arrows/WASD] move   [R] new maze")

        elif state == "human_done":
            draw_maze(grid, height, width, [], [], None, None, human_pos, start, goal, trail=human_trail)
            draw_panel(f"You reached the goal in {human_steps} steps!   [ENTER] menu   [R] new maze")

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()