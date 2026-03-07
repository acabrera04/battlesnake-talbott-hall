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
        # Add all body segments except the tail (tail will move unless snake just ate)
        tail_stacked = len(body) >= 2 and pos_tuple(body[-1]) == pos_tuple(body[-2])
        for i, seg in enumerate(body):
            if i == len(body) - 1 and not tail_stacked:
                continue  # tail will move, so it's walkable
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

    directions = ["up", "down", "left", "right"]

    # --- Score each move ---
    move_scores = {}

    for d in directions:
        new_head = add_dir(my_head, d)

        # Eliminate immediately fatal moves
        if not in_bounds(new_head, width, height):
            continue
        nh = pos_tuple(new_head)
        if nh in occupied:
            continue

        score = 0.0

        # Flood fill space from this move
        # Temporarily add our current head to occupied (our body shifts)
        sim_occupied = occupied | {pos_tuple(my_head)}
        # Remove our tail (it will move)
        tail_t = pos_tuple(my_body[-1])
        sim_occupied.discard(tail_t)
        space = flood_fill(new_head, sim_occupied, width, height)

        # If space is less than our length, this is very dangerous
        if space < my_length:
            score -= 500
        elif space < my_length * 2:
            score -= 50
        else:
            score += min(space, 80)  # reward more space, capped

        # Danger zone penalty (head-to-head with equal/longer snake)
        if nh in danger_zones:
            score -= 200

        # Kill zone bonus (head-to-head with shorter snake)
        if nh in kill_zones:
            score += 30

        # Center preference
        center_x, center_y = width / 2.0, height / 2.0
        dist_to_center = abs(new_head["x"] - center_x) + abs(new_head["y"] - center_y)
        score -= dist_to_center * 2

        # Wall penalty
        if new_head["x"] == 0 or new_head["x"] == width - 1:
            score -= 5
        if new_head["y"] == 0 or new_head["y"] == height - 1:
            score -= 5

        # --- Food seeking (health-tiered) ---
        if food:
            nearest_food = min(food, key=lambda f: manhattan(new_head, f))
            food_dist = manhattan(new_head, nearest_food)

            if my_health < 25:
                # Desperate: strongly chase food
                score += max(0, 30 - food_dist) * 5
            elif my_health < 50:
                # Moderate: prefer food if convenient
                score += max(0, 20 - food_dist) * 2
            elif my_health < 75:
                score += max(0, 15 - food_dist) * 0.5
            # If health is high, no food bonus

            # Bonus if we're closer to food than enemies
            if my_health < 50:
                for f in food:
                    my_dist = manhattan(new_head, f)
                    closest_enemy_dist = 999
                    for snake in board["snakes"]:
                        if snake["id"] == me["id"]:
                            continue
                        enemy_dist = manhattan(snake["head"], f)
                        closest_enemy_dist = min(closest_enemy_dist, enemy_dist)
                    if my_dist < closest_enemy_dist and my_dist <= 3:
                        score += 15

            # On food? bonus when hungry
            for f in food:
                if pos_tuple(new_head) == pos_tuple(f) and my_health < 40:
                    score += 40

        # --- Tail chasing (default safe behavior) ---
        my_tail = my_body[-1]
        tail_dist = manhattan(new_head, my_tail)
        # Bonus for being near our own tail (safe fallback)
        if my_health > 50:
            score += max(0, 15 - tail_dist) * 2

        # --- Aggression: cut off smaller snakes ---
        for snake in board["snakes"]:
            if snake["id"] == me["id"]:
                continue
            if my_length > snake["length"] + 1:
                # We're bigger — move toward them
                enemy_dist = manhattan(new_head, snake["head"])
                if enemy_dist <= 4:
                    score += max(0, 8 - enemy_dist) * 3

        # --- Count available moves from new position (freedom of movement) ---
        future_moves = 0
        for nb in neighbors(new_head):
            if in_bounds(nb, width, height) and pos_tuple(nb) not in sim_occupied:
                future_moves += 1
        score += future_moves * 8

        move_scores[d] = score

    # --- Choose best move ---
    if not move_scores:
        # No safe moves at all — try to pick least bad option
        # Prefer moving into tail (it'll move) or enemy we can beat
        for d in directions:
            new_head = add_dir(my_head, d)
            if in_bounds(new_head, width, height):
                move_scores[d] = -1000
                # Slightly prefer tail cell
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
