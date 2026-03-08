import random
import typing
from collections import deque


def info() -> typing.Dict:
    print("INFO")
    return {
        "apiversion": "1",
        "author": "talbott-hall",
        "color": "#ffffff",
        "head": "evil",
        "tail": "bolt",
    }


def start(game_state: typing.Dict):
    print("GAME START")


def end(game_state: typing.Dict):
    print("GAME OVER\n")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def coord(x, y):
    return {"x": x, "y": y}


def add_dir(pos, direction):
    moves = {"up": (0, 1), "down": (0, -1), "left": (-1, 0), "right": (1, 0)}
    dx, dy = moves[direction]
    return coord(pos["x"] + dx, pos["y"] + dy)


def pos_tuple(p):
    return (p["x"], p["y"])


def manhattan(a, b):
    return abs(a["x"] - b["x"]) + abs(a["y"] - b["y"])


def in_bounds(p, width, height):
    return 0 <= p["x"] < width and 0 <= p["y"] < height


def neighbors(p):
    return [
        coord(p["x"], p["y"] + 1),
        coord(p["x"], p["y"] - 1),
        coord(p["x"] - 1, p["y"]),
        coord(p["x"] + 1, p["y"]),
    ]


def build_grid(game_state):
    """Build a set of occupied cells and sets for danger/kill zones."""
    board = game_state["board"]
    width, height = board["width"], board["height"]
    me = game_state["you"]
    my_id = me["id"]
    my_length = me["length"]
    my_head = me["head"]

    occupied = set()
    danger_zones = set()  # cells adjacent to enemy heads where enemy >= my length
    kill_zones = set()    # cells adjacent to enemy heads where enemy < my length

    for snake in board["snakes"]:
        body = snake["body"]
        # Tail is walkable unless snake just ate (tail stacked = just ate)
        tail_stacked = len(body) >= 2 and pos_tuple(body[-1]) == pos_tuple(body[-2])
        for i, seg in enumerate(body):
            if i == len(body) - 1 and not tail_stacked:
                continue
            occupied.add(pos_tuple(seg))

        # Mark danger/kill zones around enemy heads
        if snake["id"] != my_id:
            enemy_head = snake["head"]
            enemy_length = snake["length"]
            for nb in neighbors(enemy_head):
                if not in_bounds(nb, width, height):
                    continue
                t = pos_tuple(nb)
                if t == pos_tuple(my_head):
                    continue
                if enemy_length >= my_length:
                    danger_zones.add(t)
                else:
                    kill_zones.add(t)

    return occupied, danger_zones, kill_zones


def flood_fill(start_pos, occupied, width, height):
    """BFS flood fill. Returns count of reachable cells."""
    sp = pos_tuple(start_pos)
    if sp in occupied:
        return 0
    visited = {sp}
    queue = deque([start_pos])
    count = 0
    while queue:
        cell = queue.popleft()
        count += 1
        for nb in neighbors(cell):
            nt = pos_tuple(nb)
            if in_bounds(nb, width, height) and nt not in visited and nt not in occupied:
                visited.add(nt)
                queue.append(nb)
    return count


def build_sim_occupied(my_head, my_body, occupied):
    """Build the simulated occupied set for after we move (body shifts)."""
    sim = occupied | {pos_tuple(my_head)}
    sim.discard(pos_tuple(my_body[-1]))
    return sim


def voronoi_territory(heads, occupied, width, height):
    """Multi-source BFS from all snake heads. Returns dict of head_tuple -> cell count.
    Each open cell is "owned" by whichever snake head can reach it first.
    Ties go to no one (contested)."""
    owner = {}  # cell_tuple -> head_tuple
    dist = {}   # cell_tuple -> distance
    queue = deque()
    counts = {}

    for h in heads:
        ht = pos_tuple(h)
        if ht in occupied:
            continue
        owner[ht] = ht
        dist[ht] = 0
        queue.append((h, 0, ht))
        counts[ht] = 1

    while queue:
        cell, d, src = queue.popleft()
        for nb in neighbors(cell):
            nt = pos_tuple(nb)
            if not in_bounds(nb, width, height) or nt in occupied:
                continue
            if nt in dist:
                if dist[nt] == d + 1 and owner[nt] != src:
                    # Tie — mark contested by removing from owner's count
                    if owner[nt] is not None:
                        counts[owner[nt]] = counts.get(owner[nt], 1) - 1
                        owner[nt] = None
                continue
            owner[nt] = src
            dist[nt] = d + 1
            counts[src] = counts.get(src, 0) + 1
            queue.append((nb, d + 1, src))

    return counts


def bfs_distance(start_pos, target_pos, occupied, width, height):
    """BFS shortest path distance. Returns distance or -1 if unreachable."""
    sp = pos_tuple(start_pos)
    tp = pos_tuple(target_pos)
    if sp == tp:
        return 0
    visited = {sp}
    queue = deque([(start_pos, 0)])
    while queue:
        cell, dist = queue.popleft()
        for nb in neighbors(cell):
            nt = pos_tuple(nb)
            if not in_bounds(nb, width, height) or nt in visited:
                continue
            if nt in occupied:
                if nt != tp:
                    continue
            if nt == tp:
                return dist + 1
            visited.add(nt)
            queue.append((nb, dist + 1))
    return -1


def bfs_to_targets(start_pos, targets, occupied, width, height):
    """BFS from start to any of the target positions. Returns (target, distance) or None."""
    target_set = set(pos_tuple(t) for t in targets)
    if not target_set:
        return None
    sp = pos_tuple(start_pos)
    if sp in target_set:
        return (start_pos, 0)
    visited = {sp}
    queue = deque([(start_pos, 0)])
    while queue:
        cell, dist = queue.popleft()
        for nb in neighbors(cell):
            nt = pos_tuple(nb)
            if not in_bounds(nb, width, height) or nt in visited:
                continue
            if nt in target_set:
                return (nb, dist + 1)
            if nt in occupied:
                continue
            visited.add(nt)
            queue.append((nb, dist + 1))
    return None


def can_reach_tail_after(new_head, my_body, occupied, width, height):
    """Check if we can reach our own tail from new_head (with updated body)."""
    # Simulate body after moving to new_head (no food eaten)
    new_body = [pos_tuple(new_head)] + [pos_tuple(s) for s in my_body[:-1]]
    sim_occupied = (occupied - {pos_tuple(my_body[-1])}) | set(new_body)
    # Tail of new body is the escape target
    tail = my_body[-1]  # the old tail position is now free
    tail_t = pos_tuple(tail)
    if tail_t in sim_occupied:
        sim_occupied.discard(tail_t)
    dist = bfs_distance(new_head, tail, sim_occupied, width, height)
    return dist > 0


# ---------------------------------------------------------------------------
# Main move logic
# ---------------------------------------------------------------------------

def move(game_state: typing.Dict) -> typing.Dict:
    board = game_state["board"]
    width, height = board["width"], board["height"]
    me = game_state["you"]
    my_head = me["head"]
    my_body = me["body"]
    my_health = me["health"]
    my_length = me["length"]

    occupied, danger_zones, kill_zones = build_grid(game_state)
    food = board["food"]
    num_snakes = len(board["snakes"])

    directions = ["up", "down", "left", "right"]

    # --- Score each move ---
    move_scores = {}

    sim_occupied = build_sim_occupied(my_head, my_body, occupied)

    # Identify larger enemies for flee logic
    larger_enemies = []
    for snake in board["snakes"]:
        if snake["id"] == me["id"]:
            continue
        if snake["length"] >= my_length:
            larger_enemies.append(snake)

    for d in directions:
        new_head = add_dir(my_head, d)

        # Eliminate immediately fatal moves
        if not in_bounds(new_head, width, height):
            continue
        nh = pos_tuple(new_head)
        if nh in occupied:
            continue

        score = 0.0

        # --- Flood fill space ---
        space = flood_fill(new_head, sim_occupied, width, height)

        if space < my_length:
            score -= 500
        elif space < my_length * 2:
            score -= 50
        else:
            score += min(space, 80)

        # --- Voronoi territory: how much space do we actually own? ---
        all_heads = [new_head]
        for snake in board["snakes"]:
            if snake["id"] == me["id"]:
                continue
            all_heads.append(snake["head"])
        territory = voronoi_territory(all_heads, sim_occupied, width, height)
        my_territory = territory.get(pos_tuple(new_head), 0)

        # Reward territory — this is space only WE can reach first
        if my_territory < my_length:
            score -= 60  # we own less space than our body needs
        else:
            score += min(my_territory, 50) * 0.8

        # --- Flee from larger enemies when we're smaller ---
        if larger_enemies:
            for enemy in larger_enemies:
                enemy_head = enemy["head"]
                # Distance before vs after this move
                old_dist = manhattan(my_head, enemy_head)
                new_dist = manhattan(new_head, enemy_head)

                if enemy["length"] > my_length + 2:
                    # Much bigger — strongly avoid getting close
                    if new_dist <= 3:
                        score -= (4 - new_dist) * 15
                    if new_dist > old_dist:
                        score += 10  # reward moving away
                    elif new_dist < old_dist:
                        score -= 10  # penalize moving toward
                else:
                    # Slightly bigger — moderate avoidance
                    if new_dist <= 2:
                        score -= (3 - new_dist) * 8

            # "Pinched between two large snakes" detection
            if len(larger_enemies) >= 2:
                close_enemies = [e for e in larger_enemies
                                 if manhattan(new_head, e["head"]) <= 4]
                if len(close_enemies) >= 2:
                    # We're between multiple large snakes — heavy penalty
                    avg_dist = sum(manhattan(new_head, e["head"])
                                   for e in close_enemies) / len(close_enemies)
                    if avg_dist <= 3:
                        score -= 50

        # --- Tail reachability check ---
        # Penalize moves where we can't reach our own tail (risk of self-trap)
        if not can_reach_tail_after(new_head, my_body, occupied, width, height):
            if space < my_length * 3:
                # Can't reach tail AND limited space = very dangerous
                score -= 150
            else:
                # Can't reach tail but lots of space — mild concern
                score -= 30

        # --- Danger zone penalty (head-to-head with equal/longer snake) ---
        if nh in danger_zones:
            score -= 200

        # --- Kill zone bonus (head-to-head with shorter snake) ---
        if nh in kill_zones:
            score += 30

        # --- Center preference ---
        center_x, center_y = width / 2.0, height / 2.0
        dist_to_center = abs(new_head["x"] - center_x) + abs(new_head["y"] - center_y)
        score -= dist_to_center * 2

        # --- Mild wall penalty (contextual, not overwhelming) ---
        nx, ny = new_head["x"], new_head["y"]
        on_x_wall = nx == 0 or nx == width - 1
        on_y_wall = ny == 0 or ny == height - 1
        if on_x_wall:
            score -= 10
        if on_y_wall:
            score -= 10
        # Corner is extra bad
        if on_x_wall and on_y_wall:
            score -= 10

        # --- Food seeking using BFS (actual pathfinding, not manhattan) ---
        if food:
            # Find nearest food by BFS from new position
            bfs_food = bfs_to_targets(new_head, food, sim_occupied, width, height)
            if bfs_food:
                _, food_dist = bfs_food
            else:
                food_dist = 999

            # Also check: are we stepping directly onto food?
            on_food = nh in {pos_tuple(f) for f in food}

            if my_health < 25:
                score += max(0, 30 - food_dist) * 5
                if on_food:
                    score += 60
            elif my_health < 50:
                score += max(0, 20 - food_dist) * 2
                if on_food:
                    score += 30
            elif my_health < 75:
                score += max(0, 15 - food_dist) * 0.5

            # Food contest detection: don't step onto food if an equal/larger
            # enemy can also step onto it this turn (head-to-head death)
            if on_food:
                for snake in board["snakes"]:
                    if snake["id"] == me["id"]:
                        continue
                    enemy_dist = manhattan(snake["head"], new_head)
                    if enemy_dist <= 1 and snake["length"] >= my_length:
                        score -= 100

            # Bonus if we're closer to food than enemies (use BFS dist)
            if my_health < 50 and bfs_food:
                food_target, my_food_dist = bfs_food
                for snake in board["snakes"]:
                    if snake["id"] == me["id"]:
                        continue
                    enemy_food_dist = manhattan(snake["head"], food_target)
                    if my_food_dist < enemy_food_dist and my_food_dist <= 3:
                        score += 15
                        break  # one bonus is enough

        # --- Tail chasing (default safe behavior) ---
        my_tail = my_body[-1]
        tail_dist = manhattan(new_head, my_tail)
        if my_health > 50:
            score += max(0, 15 - tail_dist) * 2

        # --- Aggression: game-phase aware ---
        for snake in board["snakes"]:
            if snake["id"] == me["id"]:
                continue
            enemy_head = snake["head"]
            enemy_length = snake["length"]

            if my_length > enemy_length + 1:
                enemy_dist = manhattan(new_head, enemy_head)
                if num_snakes == 2:
                    # 1v1: aggressively cut them off
                    if enemy_dist <= 6:
                        score += max(0, 10 - enemy_dist) * 5
                else:
                    # Multi-snake: moderate aggression
                    if enemy_dist <= 4:
                        score += max(0, 8 - enemy_dist) * 3

        # --- Freedom of movement from new position ---
        future_moves = 0
        for nb in neighbors(new_head):
            if in_bounds(nb, width, height) and pos_tuple(nb) not in sim_occupied:
                future_moves += 1
        score += future_moves * 5

        move_scores[d] = score

    # --- Choose best move ---
    if not move_scores:
        for d in directions:
            new_head = add_dir(my_head, d)
            if in_bounds(new_head, width, height):
                move_scores[d] = -1000
                if pos_tuple(new_head) == pos_tuple(my_body[-1]):
                    move_scores[d] = -100

    if not move_scores:
        print(f"MOVE {game_state['turn']}: No moves at all! Moving up")
        return {"move": "up"}

    best_move = max(move_scores, key=move_scores.get)
    print(f"MOVE {game_state['turn']}: {best_move} (score: {move_scores[best_move]:.0f})")
    return {"move": best_move}


if __name__ == "__main__":
    from server import run_server
    run_server({"info": info, "start": start, "move": move, "end": end})
