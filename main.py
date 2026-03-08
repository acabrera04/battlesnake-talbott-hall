"""Battlesnake game logic and move-selection heuristics."""

# Welcome to
# __________         __    __  .__                               __
# \______   \_____ _/  |__/  |_|  |   ____   ______ ____ _____  |  | __ ____
#  |    |  _/\__  \\   __\   __\  | _/ __ \ /  ___//    \\__  \ |  |/ // __ \
#  |    |   \ / __ \|  |  |  | |  |_\  ___/ \___ \|   |  \/ __ \|    <\  ___/
#  |________/(______/__|  |__| |____/\_____>______>___|__(______/__|__\\_____>
#
# This file can be a nice home for your Battlesnake logic and helper functions.
#
# To get you started we've included code to prevent your Battlesnake from moving backwards.
# For more info see docs.battlesnake.com

import random
import time
import typing


Point = typing.Tuple[int, int]
SnakeApiObject = typing.Dict[str, typing.Any]


# Scoring weights and thresholds for move selection.
ILLEGAL_MOVE_PENALTY = -1000000
LEGAL_MOVE_SCORE = 1
DANGER_ZONE_PENALTY = 1000

STARVING_HEALTH_THRESHOLD = 25
LOW_HEALTH_THRESHOLD = 50
MID_HEALTH_THRESHOLD = 75

STARVING_FOOD_WEIGHT = 10
LOW_FOOD_WEIGHT = 2
MID_FOOD_WEIGHT = 1
HIGH_FOOD_WEIGHT = 0

ADJACENT_FOOD_DISTANCE = 1
ADJACENT_FOOD_HEALTH_THRESHOLD = 50
ADJACENT_FOOD_BONUS = 50

TAIL_CHASE_HEALTH_THRESHOLD = 30
TAIL_CHASE_RANGE = 10
TAIL_CHASE_BASE_WEIGHT = 5
TAIL_CHASE_LENGTH_SCALE = 0.2

ENEMY_AVOIDANCE_RANGE = 3
ENEMY_AVOIDANCE_WEIGHT = 4

AGGRESSION_RANGE = 4
AGGRESSION_CHASE_WEIGHT = 6

HEAD_TO_HEAD_PENALTY = 10000
SMALLER_HEAD_TO_HEAD_BONUS = 50
SMALLER_HEAD_TO_HEAD_PENALTY = 10
BODY_BLOCK_STANDOFF_DISTANCE = 2
BODY_BLOCK_STANDOFF_BONUS = 30

LOOKAHEAD_FREEDOM_WEIGHT = 15
LOOKAHEAD_DEAD_END_PENALTY = 200
DEEP_LOOKAHEAD_MIN_DEPTH = 2
DEEP_LOOKAHEAD_MAX_DEPTH = 8
DEEP_LOOKAHEAD_TIME_BUDGET_MS = 200
DEEP_LOOKAHEAD_WEIGHT = 20

FLOOD_FILL_TRAP_PENALTY = 3000000
FLOOD_FILL_TIGHT_PENALTY = 500

CENTER_PREFERENCE_WEIGHT = 4
CUTOFF_BONUS_WEIGHT = 8
CUTOFF_SPACE_SAMPLE = 30
LARGER_CUTOFF_RANGE = 6
LARGER_CUTOFF_LENGTH_MARGIN = 4
LARGER_CUTOFF_BONUS_WEIGHT = 10
CONTESTED_FOOD_DISCOUNT = 0.3

BODY_PROXIMITY_PENALTY = 12

DENSITY_RADIUS = 4
DENSITY_PENALTY = 15

OVERGROWN_LENGTH_THRESHOLD = 20
OVERGROWN_FOOD_AVOID_WEIGHT = 8
OVERGROWN_ADJACENT_FOOD_PENALTY = 120
OVERGROWN_AVOID_DISABLE_HEALTH = 50
MAX_HEALTH = 100


# info is called when you create your Battlesnake on play.battlesnake.com
# and controls your Battlesnake's appearance
# TIP: If you open your Battlesnake URL in a browser you should see this data
def info() -> typing.Dict[str, str]:
    """Return Battlesnake metadata used by the game engine."""
    print("INFO")

    return {
        "apiversion": "1",
        "author": "",  # TODO: Your Battlesnake Username
        "color": "#888888",  # TODO: Choose color
        "head": "default",  # TODO: Choose head
        "tail": "default",  # TODO: Choose tail
    }


# start is called when your Battlesnake begins a game
def start(game_state: SnakeApiObject) -> None:
    """Handle game start events."""
    print("GAME START")


# end is called when your Battlesnake finishes a game
def end(game_state: SnakeApiObject) -> None:
    """Handle game end events."""
    print("GAME OVER\n")

def text_to_tuple(p: typing.Dict[str, int]) -> Point:
    """Convert an API point dict to an (x, y) tuple."""
    return (p['x'], p['y'])

def tuple_to_text(p: Point) -> typing.Dict[str, int]:
    """Convert an (x, y) tuple to an API point dict."""
    return {'x': p[0], 'y': p[1]}

# returns tuples of the 4 adjacent squares to p
def moveset(p: Point) -> typing.List[Point]:
    """Return the four orthogonally adjacent squares to a point."""
    return [
        (p[0]+1, p[1]),
        (p[0]-1, p[1]),
        (p[0], p[1]+1),
        (p[0], p[1]-1),
    ]

def in_bounds(p: Point, width: int, height: int) -> bool:
    """Return True when a point is inside board bounds."""
    return 0 <= p[0] < width and 0 <= p[1] < height

def build_board(game_state: SnakeApiObject) -> typing.Tuple[
    typing.List[Point],
    typing.Set[Point],
    typing.Set[Point],
    typing.Set[Point],
]:
    """Build derived board state: food, occupied cells, and danger zones."""
    board_width = game_state['board']['width']
    board_height = game_state['board']['height']

    self_length = len(game_state['you']['body'])
    self_head = text_to_tuple(game_state['you']['head'])

    can_die: typing.Set[Point] = set()
    can_kill: typing.Set[Point] = set()
    occupied: typing.Set[Point] = set()

    for snake in game_state['board']['snakes']:

        if snake['id'] == game_state['you']['id']:
            # our tail is occupied if we just ate food, otherwise it's not since it will move forward next turn
            eaten = len(snake['body']) > 2 and text_to_tuple(snake['body'][-1]) == text_to_tuple(snake['body'][-2]) 

            # populate body based on whether we just ate or not
            for i, segment in enumerate(snake['body']): 
                if i == len(snake['body']) - 1 and not eaten: # skip tail if we didn't just eat
                    continue
                occupied.add(text_to_tuple(segment))

        else: # determine death and murder zones for enemy snakes based on length
            enemy_len = len(snake['body'])
            enemy_head = text_to_tuple(snake['head'])

            # enemy body segments are occupied, but skip tail if they didn't just eat
            enemy_eaten = len(snake['body']) > 2 and text_to_tuple(snake['body'][-1]) == text_to_tuple(snake['body'][-2])
            for i, segment in enumerate(snake['body']):
                if i == len(snake['body']) - 1 and not enemy_eaten:
                    continue
                occupied.add(text_to_tuple(segment))

            for m in moveset(enemy_head):
                if in_bounds(m, board_width, board_height):
                    if m in occupied: # ignore our own head
                        continue
                    elif enemy_len >= self_length:
                        can_die.add(m)
                    else:
                        can_kill.add(m)

    food = [text_to_tuple(food) for food in game_state['board']['food']]

    return food, occupied, can_die, can_kill

def next_from_dir(head: Point, direction: str) -> Point:
    """Return the next head position for a given move direction."""
    if direction == "up":
        return (head[0], head[1] + 1)
    elif direction == "down":
        return (head[0], head[1] - 1)
    elif direction == "left":
        return (head[0] - 1, head[1])
    elif direction == "right":
        return (head[0] + 1, head[1])
    raise ValueError(f"invalid direction: {direction}")

def manhattan_distance(
    point: Point,
    food: typing.List[Point],
) -> int:
    """Compute Manhattan distance from a point to the nearest target point."""
    return min(abs(point[0] - f[0]) + abs(point[1] - f[1]) for f in food)

def get_enemy_targets(
    game_state: SnakeApiObject,
) -> typing.Tuple[typing.List[Point], typing.List[Point], typing.List[Point], typing.List[Point]]:
    """Collect enemy body/head targets used by avoidance and aggression heuristics.

    Returns:
        threat_positions: body segments of equal/larger snakes
        smaller_heads: heads of snakes we can beat head-to-head
        all_enemy_heads: every enemy head
        near_larger_heads: heads of snakes slightly longer than us (1-LARGER_CUTOFF_LENGTH_MARGIN)
            that we should try to cut off without engaging directly
    """
    threat_positions: typing.List[Point] = []
    smaller_heads: typing.List[Point] = []
    all_enemy_heads: typing.List[Point] = []
    near_larger_heads: typing.List[Point] = []
    you_id = game_state['you']['id']
    self_length = len(game_state['you']['body'])

    for snake in game_state['board']['snakes']:
        if snake['id'] == you_id:
            continue
        enemy_head = text_to_tuple(snake['head'])
        enemy_length = len(snake['body'])
        all_enemy_heads.append(enemy_head)

        if enemy_length >= self_length:
            for segment in snake['body']:
                threat_positions.append(text_to_tuple(segment))
            # snakes 1-LARGER_CUTOFF_LENGTH_MARGIN longer: dangerous to fight, viable to box in
            if self_length <= enemy_length <= self_length + LARGER_CUTOFF_LENGTH_MARGIN:
                near_larger_heads.append(enemy_head)
        else:
            smaller_heads.append(enemy_head)

    return threat_positions, smaller_heads, all_enemy_heads, near_larger_heads

def count_safe_followup_moves(
    head: Point,
    occupied: typing.Set[Point],
    can_die: typing.Set[Point],
    enemy_head_collision_squares: typing.Set[Point],
    width: int,
    height: int,
) -> int:
    """Count legal, low-risk follow-up squares from a candidate head position."""
    safe_moves = 0

    for next_square in moveset(head):
        if not in_bounds(next_square, width, height):
            continue
        if next_square in occupied:
            continue
        if next_square in can_die:
            continue
        if next_square in enemy_head_collision_squares:
            continue
        safe_moves += 1

    return safe_moves

def flood_fill_reachable_space(
    start: Point,
    occupied: typing.Set[Point],
    width: int,
    height: int,
    max_cells: typing.Optional[int] = None,
) -> int:
    """Estimate reachable open space from a start point using flood fill."""
    if start in occupied or not in_bounds(start, width, height):
        return 0

    visited: typing.Set[Point] = set()
    stack: typing.List[Point] = [start]

    while stack:
        current = stack.pop()
        if current in visited:
            continue
        if current in occupied:
            continue
        if not in_bounds(current, width, height):
            continue

        visited.add(current)
        if max_cells is not None and len(visited) >= max_cells:
            return len(visited)

        for neighbor in moveset(current):
            if neighbor not in visited:
                stack.append(neighbor)

    return len(visited)

def distance_to_board_center(point: Point, width: int, height: int) -> int:
    """Return Manhattan distance to the nearest board center cell."""
    center_x_candidates = {(width - 1) // 2, width // 2}
    center_y_candidates = {(height - 1) // 2, height // 2}

    return min(
        abs(point[0] - center_x) + abs(point[1] - center_y)
        for center_x in center_x_candidates
        for center_y in center_y_candidates
    )

class _SearchTimeout(Exception):
    """Raised when the lookahead time budget is exhausted."""


def _simulate_enemy_moves(
    head: Point,
    occupied: typing.Set[Point],
    enemy_heads: typing.List[Point],
    width: int,
    height: int,
) -> typing.Tuple[typing.Set[Point], typing.List[Point]]:
    """Simulate enemy heads greedily chasing our head by one step."""
    new_enemy_heads: typing.List[Point] = []
    new_occupied = set(occupied)
    new_occupied.add(head)
    for eh in enemy_heads:
        best_move = eh
        best_dist = abs(eh[0] - head[0]) + abs(eh[1] - head[1])
        for em in moveset(eh):
            if in_bounds(em, width, height) and em not in new_occupied:
                d = abs(em[0] - head[0]) + abs(em[1] - head[1])
                if d < best_dist:
                    best_dist = d
                    best_move = em
        new_enemy_heads.append(best_move)
        new_occupied.add(best_move)
    return new_occupied, new_enemy_heads


def _evaluate_position(
    head: Point,
    occupied: typing.Set[Point],
    width: int,
    height: int,
) -> float:
    """Static evaluation: count open neighbours as a quick survival heuristic."""
    score = 0.0
    for m in moveset(head):
        if in_bounds(m, width, height) and m not in occupied:
            score += 1.0
    return score


def deep_lookahead_score(
    head: Point,
    occupied: typing.Set[Point],
    enemy_heads: typing.List[Point],
    width: int,
    height: int,
    depth: int,
    alpha: float = float('-inf'),
    beta: float = float('inf'),
    deadline: typing.Optional[float] = None,
) -> float:
    """Alpha-beta search scoring positions by survival potential.

    Maximises over our moves and minimises over enemy responses (modelled
    as greedy chase).  Alpha-beta bounds prune branches that cannot affect
    the final choice, significantly reducing the search tree.

    Raises _SearchTimeout when *deadline* (a ``time.monotonic`` timestamp)
    is exceeded so that iterative deepening can fall back to the previous
    completed depth.
    """
    if deadline is not None and time.monotonic() >= deadline:
        raise _SearchTimeout

    if depth <= 0:
        return _evaluate_position(head, occupied, width, height)

    legal_moves: typing.List[Point] = []
    for m in moveset(head):
        if in_bounds(m, width, height) and m not in occupied:
            legal_moves.append(m)

    if not legal_moves:
        return -1.0  # dead end

    # simulate enemy heads moving one step toward us (greedy)
    new_occupied, new_enemy_heads = _simulate_enemy_moves(
        head, occupied, enemy_heads, width, height,
    )

    best = float('-inf')
    for m in legal_moves:
        child_score = 1.0 + 0.5 * deep_lookahead_score(
            m, new_occupied, new_enemy_heads, width, height, depth - 1, alpha, beta, deadline,
        )
        if child_score > best:
            best = child_score
        if best > alpha:
            alpha = best
        if alpha >= beta:
            break  # prune remaining branches
    return best


def iterative_deepening_score(
    head: Point,
    occupied: typing.Set[Point],
    enemy_heads: typing.List[Point],
    width: int,
    height: int,
    deadline: float,
) -> float:
    """Run alpha-beta at increasing depths until the time budget runs out.

    Returns the score from the deepest fully completed search.
    """
    best_score = _evaluate_position(head, occupied, width, height)

    for depth in range(DEEP_LOOKAHEAD_MIN_DEPTH, DEEP_LOOKAHEAD_MAX_DEPTH + 1):
        try:
            score = deep_lookahead_score(
                head, occupied, enemy_heads, width, height, depth,
                deadline=deadline,
            )
            best_score = score
        except _SearchTimeout:
            break

    return best_score


# move is called on every turn and returns your next move
# Valid moves are "up", "down", "left", or "right"
# See https://docs.battlesnake.com/api/example-move for available data
def move(game_state: SnakeApiObject) -> typing.Dict[str, str]:
    """Score legal directions and return the highest-valued next move."""

    # set deadline for iterative deepening search
    lookahead_deadline = time.monotonic() + DEEP_LOOKAHEAD_TIME_BUDGET_MS / 1000.0

    # load board state
    food, occupied, can_die, can_kill = build_board(game_state)

    # collect tail positions that will vacate next turn (for smarter flood fill)
    moving_tails: typing.Set[Point] = set()
    for snake in game_state['board']['snakes']:
        eaten = len(snake['body']) > 2 and text_to_tuple(snake['body'][-1]) == text_to_tuple(snake['body'][-2])
        if not eaten:
            moving_tails.add(text_to_tuple(snake['body'][-1]))
    # occupied_with_tails includes tails (more conservative view for flood fill)
    occupied_with_tails = occupied | moving_tails

    # init move scores
    directions = ['up', 'down', 'left', 'right']
    moves = {direction: 0 for direction in directions}
    health = game_state['you']['health']
    self_length = len(game_state['you']['body'])
    board_width = game_state['board']['width']
    board_height = game_state['board']['height']
    threat_enemy_positions, smaller_enemy_heads, all_enemy_heads, near_larger_enemy_heads = get_enemy_targets(game_state)

    # collect all enemy body segments for density scoring (all snakes, all segments)
    you_id = game_state['you']['id']
    all_enemy_segments: typing.List[Point] = [
        text_to_tuple(seg)
        for snake in game_state['board']['snakes']
        if snake['id'] != you_id
        for seg in snake['body']
    ]

    dangerous_head_collision_squares: typing.Set[Point] = set()
    killable_head_collision_squares: typing.Set[Point] = set()
    for enemy_head in all_enemy_heads:
        is_smaller = enemy_head in smaller_enemy_heads
        for square in moveset(enemy_head):
            if in_bounds(square, board_width, board_height):
                if is_smaller:
                    killable_head_collision_squares.add(square)
                else:
                    dangerous_head_collision_squares.add(square)
    enemy_head_collision_squares = dangerous_head_collision_squares | killable_head_collision_squares

    for d in directions:
        # calculate new head position based on move direction
        new_head = next_from_dir(text_to_tuple(game_state['you']['head']), d)

        # hard-penalize illegal moves so direction choice uses score only
        if new_head in occupied or not in_bounds(new_head, board_width, board_height):
            moves[d] = ILLEGAL_MOVE_PENALTY
            continue

        # flood-fill lookahead: use tail-aware flood fill for a realistic view
        # tails will vacate next turn, so the real available space is larger
        region_space = flood_fill_reachable_space(
            new_head,
            occupied,
            board_width,
            board_height,
            max_cells=self_length * 2,
        )
        if region_space < self_length:
            # hard trap: even counting current occupied cells we can't fit
            moves[d] -= FLOOD_FILL_TRAP_PENALTY
            continue
        elif region_space < self_length * 2:
            # tight space: survivable but risky, apply softer penalty
            tightness = 1.0 - (region_space - self_length) / max(1, self_length)
            moves[d] -= int(FLOOD_FILL_TIGHT_PENALTY * max(0.0, tightness))

        # baseline score for legal moves
        moves[d] += LEGAL_MOVE_SCORE

        # prefer staying closer to the center to reduce corner-trap risk
        # disable when hungry so food-seeking isn't penalized for edge food
        if health >= LOW_HEALTH_THRESHOLD:
            center_distance = distance_to_board_center(new_head, board_width, board_height)
            moves[d] -= center_distance * CENTER_PREFERENCE_WEIGHT

        # prefer moves with some breathing room from surrounding bodies/walls
        occupied_neighbors = sum(1 for neighbor in moveset(new_head) if neighbor in occupied)
        moves[d] -= occupied_neighbors * BODY_PROXIMITY_PENALTY

        # avoid high-density zones: penalise each enemy segment within DENSITY_RADIUS
        # this catches crowded corners/edges that flood fill misses (space exists today but not next turn)
        if all_enemy_segments:
            nearby_segments = sum(
                1 for seg in all_enemy_segments
                if abs(seg[0] - new_head[0]) + abs(seg[1] - new_head[1]) <= DENSITY_RADIUS
            )
            moves[d] -= nearby_segments * DENSITY_PENALTY

        # avoid risky head-to-head zones against equal/larger snakes
        if new_head in can_die:
            moves[d] -= DANGER_ZONE_PENALTY

        # avoid direct head-to-head squares against equal/larger snakes
        if new_head in dangerous_head_collision_squares:
            moves[d] -= HEAD_TO_HEAD_PENALTY

        # reward head-to-head squares against smaller snakes (we win the collision)
        if new_head in killable_head_collision_squares:
            moves[d] += SMALLER_HEAD_TO_HEAD_BONUS

        # can_kill is the smaller-snake head contest zone; small penalty to avoid accidental ties
        if new_head in can_kill:
            moves[d] -= SMALLER_HEAD_TO_HEAD_PENALTY

        # apply a small penalty when moving near enemy snakes
        if threat_enemy_positions:
            nearest_enemy_distance = manhattan_distance(new_head, threat_enemy_positions)
            if nearest_enemy_distance <= ENEMY_AVOIDANCE_RANGE:
                proximity_penalty = (ENEMY_AVOIDANCE_RANGE + 1 - nearest_enemy_distance) * ENEMY_AVOIDANCE_WEIGHT
                moves[d] -= proximity_penalty

        # pressure smaller snakes while maintaining a one-tile buffer from head-to-head collisions
        if smaller_enemy_heads:
            nearest_smaller_head_distance = manhattan_distance(new_head, smaller_enemy_heads)
            if nearest_smaller_head_distance == BODY_BLOCK_STANDOFF_DISTANCE:
                moves[d] += BODY_BLOCK_STANDOFF_BONUS
            elif 1 < nearest_smaller_head_distance <= AGGRESSION_RANGE:
                aggression_bonus = (AGGRESSION_RANGE + 1 - nearest_smaller_head_distance) * AGGRESSION_CHASE_WEIGHT
                moves[d] += aggression_bonus

            # area control: prefer moves that cut off smaller snakes' available space
            if nearest_smaller_head_distance <= AGGRESSION_RANGE:
                nearest_small = min(smaller_enemy_heads, key=lambda h: abs(new_head[0] - h[0]) + abs(new_head[1] - h[1]))
                occupied_after_move = occupied | {new_head}
                enemy_space = flood_fill_reachable_space(
                    nearest_small, occupied_after_move, board_width, board_height, max_cells=CUTOFF_SPACE_SAMPLE,
                )
                # bonus for reducing enemy's available space
                cutoff_bonus = max(0, CUTOFF_SPACE_SAMPLE - enemy_space) * CUTOFF_BONUS_WEIGHT // CUTOFF_SPACE_SAMPLE
                moves[d] += cutoff_bonus

        # intercept slightly-larger snakes: try to cut off their space without head-to-head
        # only apply when we are NOT moving into their collision zone (head-to-head would be fatal)
        if near_larger_enemy_heads and new_head not in dangerous_head_collision_squares:
            nearest_larger = min(
                near_larger_enemy_heads,
                key=lambda h: abs(new_head[0] - h[0]) + abs(new_head[1] - h[1]),
            )
            dist_to_larger = abs(new_head[0] - nearest_larger[0]) + abs(new_head[1] - nearest_larger[1])
            if dist_to_larger <= LARGER_CUTOFF_RANGE:
                occupied_after_move = occupied | {new_head}
                enemy_space = flood_fill_reachable_space(
                    nearest_larger, occupied_after_move, board_width, board_height,
                    max_cells=CUTOFF_SPACE_SAMPLE,
                )
                cutoff_bonus = (
                    max(0, CUTOFF_SPACE_SAMPLE - enemy_space)
                    * LARGER_CUTOFF_BONUS_WEIGHT
                    // CUTOFF_SPACE_SAMPLE
                )
                moves[d] += cutoff_bonus

        # one-step lookahead: prefer moves that keep future options open
        followup_options = count_safe_followup_moves(
            new_head,
            occupied,
            can_die,
            enemy_head_collision_squares,
            board_width,
            board_height,
        )
        moves[d] += followup_options * LOOKAHEAD_FREEDOM_WEIGHT
        if followup_options == 0:
            moves[d] -= LOOKAHEAD_DEAD_END_PENALTY

        # iterative deepening lookahead: search as deep as time allows
        deep_score = iterative_deepening_score(
            new_head, occupied, all_enemy_heads, board_width, board_height, lookahead_deadline,
        )
        moves[d] += int(deep_score * DEEP_LOOKAHEAD_WEIGHT)

        # prefer moves that get closer to the nearest food
        if food:
            # find nearest food, discounting food that enemies will reach first
            nearest_food_distance = manhattan_distance(new_head, food)
            if all_enemy_heads and health >= STARVING_HEALTH_THRESHOLD:
                # check if an enemy is closer to our nearest food
                best_food_score = float('inf')
                for f in food:
                    our_dist = abs(new_head[0] - f[0]) + abs(new_head[1] - f[1])
                    enemy_dist = min(abs(eh[0] - f[0]) + abs(eh[1] - f[1]) for eh in all_enemy_heads)
                    if enemy_dist < our_dist:
                        # enemy is closer, discount this food
                        effective_dist = our_dist / CONTESTED_FOOD_DISCOUNT
                    else:
                        effective_dist = our_dist
                    best_food_score = min(best_food_score, effective_dist)
                nearest_food_distance = int(best_food_score)
            if health < STARVING_HEALTH_THRESHOLD:
                food_weight = STARVING_FOOD_WEIGHT
            elif health < LOW_HEALTH_THRESHOLD:
                food_weight = LOW_FOOD_WEIGHT
            elif health < MID_HEALTH_THRESHOLD:
                food_weight = MID_FOOD_WEIGHT
            else:
                food_weight = HIGH_FOOD_WEIGHT

            excess_length = max(0, self_length - OVERGROWN_LENGTH_THRESHOLD)
            hunger_safe_ratio = max(
                0.0,
                (health - OVERGROWN_AVOID_DISABLE_HEALTH) / (MAX_HEALTH - OVERGROWN_AVOID_DISABLE_HEALTH),
            )

            # avoid growth-inducing food when we're already long and healthy to reduce risk of self-trapping
            # this is a linear penalty based on how much we're over the length threshold and how close we are to starving
            effective_food_weight = max(
                0.0,
                food_weight - (OVERGROWN_FOOD_AVOID_WEIGHT * excess_length * hunger_safe_ratio),
            )
            moves[d] += int(effective_food_weight * (health - nearest_food_distance))

        # chase tail to encourage circular movement and avoid self-trapping
        # weight scales with length since longer snakes benefit more from staying compact
        if health > TAIL_CHASE_HEALTH_THRESHOLD:
            tail_distance = manhattan_distance(new_head, [text_to_tuple(game_state['you']['body'][-1])])
            tail_weight = TAIL_CHASE_BASE_WEIGHT + int(self_length * TAIL_CHASE_LENGTH_SCALE)
            moves[d] += max(0, TAIL_CHASE_RANGE - tail_distance) * tail_weight


    # choose among the highest-scoring directions
    best_score = max(moves.values())
    best_moves = [d for d, score in moves.items() if score == best_score]
    next_move = random.choice(best_moves)
    print(f"MOVE {game_state['turn']}: {next_move}")
    return {"move": next_move}


# Start server when `python main.py` is run
if __name__ == "__main__":
    from server import run_server

    run_server({"info": info, "start": start, "move": move, "end": end})
