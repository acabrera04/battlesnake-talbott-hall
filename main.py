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
import typing


Point = typing.Tuple[int, int]
SnakeApiObject = typing.Dict[str, typing.Any]


# Scoring weights and thresholds for move selection.
ILLEGAL_MOVE_PENALTY = -1000000
LEGAL_MOVE_SCORE = 1
DANGER_ZONE_PENALTY = 1000
KILL_ZONE_BONUS = 10

STARVING_HEALTH_THRESHOLD = 25
LOW_HEALTH_THRESHOLD = 50
MID_HEALTH_THRESHOLD = 75

STARVING_FOOD_WEIGHT = 5
LOW_FOOD_WEIGHT = 2
MID_FOOD_WEIGHT = 1
HIGH_FOOD_WEIGHT = 0

ADJACENT_FOOD_DISTANCE = 1
ADJACENT_FOOD_HEALTH_THRESHOLD = 50
ADJACENT_FOOD_BONUS = 50

TAIL_CHASE_HEALTH_THRESHOLD = 50
TAIL_CHASE_RANGE = 10
TAIL_CHASE_WEIGHT = 3

ENEMY_AVOIDANCE_RANGE = 3
ENEMY_AVOIDANCE_WEIGHT = 4


# info is called when you create your Battlesnake on play.battlesnake.com
# and controls your Battlesnake's appearance
# TIP: If you open your Battlesnake URL in a browser you should see this data
def info() -> typing.Dict[str, str]:
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
    print("GAME START")


# end is called when your Battlesnake finishes a game
def end(game_state: SnakeApiObject) -> None:
    print("GAME OVER\n")

def text_to_tuple(p: typing.Dict[str, int]) -> Point:
    return (p['x'], p['y'])

def tuple_to_text(p: Point) -> typing.Dict[str, int]:
    return {'x': p[0], 'y': p[1]}

# returns tuples of the 4 adjacent squares to p
def moveset(p: Point) -> typing.List[Point]:
    return [
        (p[0]+1, p[1]),
        (p[0]-1, p[1]),
        (p[0], p[1]+1),
        (p[0], p[1]-1),
    ]

def in_bounds(p: Point, width: int, height: int) -> bool:
    return 0 <= p[0] < width and 0 <= p[1] < height

def build_board(game_state: SnakeApiObject) -> typing.Tuple[
    typing.List[Point],
    typing.Set[Point],
    typing.Set[Point],
    typing.Set[Point],
]:
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
    return min(abs(point[0] - f[0]) + abs(point[1] - f[1]) for f in food)

def get_enemy_body_positions(game_state: SnakeApiObject) -> typing.List[Point]:
    enemy_positions: typing.List[Point] = []
    you_id = game_state['you']['id']

    for snake in game_state['board']['snakes']:
        if snake['id'] == you_id:
            continue

        for segment in snake['body']:
            enemy_positions.append(text_to_tuple(segment))

    return enemy_positions

# move is called on every turn and returns your next move
# Valid moves are "up", "down", "left", or "right"
# See https://docs.battlesnake.com/api/example-move for available data
def move(game_state: SnakeApiObject) -> typing.Dict[str, str]:

    # load board state
    food, occupied, can_die, can_kill = build_board(game_state)

    # init move scores
    directions = ['up', 'down', 'left', 'right']
    moves = {direction: 0 for direction in directions}
    health = game_state['you']['health']
    enemy_positions = get_enemy_body_positions(game_state)

    for d in directions:
        # calculate new head position based on move direction
        new_head = next_from_dir(text_to_tuple(game_state['you']['head']), d)

        # hard-penalize illegal moves so direction choice uses score only
        if new_head in occupied or not in_bounds(new_head, game_state['board']['width'], game_state['board']['height']):
            moves[d] = ILLEGAL_MOVE_PENALTY
            continue

        # baseline score for legal moves
        moves[d] += LEGAL_MOVE_SCORE

        # avoid risky head-to-head zones against equal/larger snakes
        if new_head in can_die:
            moves[d] -= DANGER_ZONE_PENALTY

        # mildly favor attack opportunities against smaller snakes
        if new_head in can_kill:
            moves[d] += KILL_ZONE_BONUS

        # apply a small penalty when moving near enemy snakes
        if enemy_positions:
            nearest_enemy_distance = manhattan_distance(new_head, enemy_positions)
            if nearest_enemy_distance <= ENEMY_AVOIDANCE_RANGE:
                proximity_penalty = (ENEMY_AVOIDANCE_RANGE + 1 - nearest_enemy_distance) * ENEMY_AVOIDANCE_WEIGHT
                moves[d] -= proximity_penalty

        # prefer moves that get closer to the nearest food
        if food:
            # use current health to determine if we want food or not (minimize length)
            nearest_food_distance = manhattan_distance(new_head, food)

            if health < STARVING_HEALTH_THRESHOLD:
                moves[d] += STARVING_FOOD_WEIGHT * (health - nearest_food_distance)
            elif health < LOW_HEALTH_THRESHOLD:
                moves[d] += LOW_FOOD_WEIGHT * (health - nearest_food_distance)
            elif health < MID_HEALTH_THRESHOLD:
                moves[d] += MID_FOOD_WEIGHT * (health - nearest_food_distance)
            else:
                moves[d] += HIGH_FOOD_WEIGHT * (health - nearest_food_distance)

            # if we are adjacent to food & slightly low on health, might as well get it
            if nearest_food_distance == ADJACENT_FOOD_DISTANCE and health < ADJACENT_FOOD_HEALTH_THRESHOLD:
                moves[d] += ADJACENT_FOOD_BONUS

        # if nothing is happening just chase tail (encourage circular movement to stay alive)
        if health > TAIL_CHASE_HEALTH_THRESHOLD:
            tail_distance = manhattan_distance(new_head, [text_to_tuple(game_state['you']['body'][-1])])
            moves[d] += max(0, TAIL_CHASE_RANGE - tail_distance) * TAIL_CHASE_WEIGHT


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
