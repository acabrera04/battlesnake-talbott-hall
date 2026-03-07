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


# info is called when you create your Battlesnake on play.battlesnake.com
# and controls your Battlesnake's appearance
# TIP: If you open your Battlesnake URL in a browser you should see this data
def info() -> typing.Dict:
    print("INFO")

    return {
        "apiversion": "1",
        "author": "",  # TODO: Your Battlesnake Username
        "color": "#888888",  # TODO: Choose color
        "head": "default",  # TODO: Choose head
        "tail": "default",  # TODO: Choose tail
    }


# start is called when your Battlesnake begins a game
def start(game_state: typing.Dict):
    print("GAME START")


# end is called when your Battlesnake finishes a game
def end(game_state: typing.Dict):
    print("GAME OVER\n")

def text_to_tuple(p):
    return (p['x'], p['y'])

def tuple_to_text(p):
    return {'x': p[0], 'y': p[1]}

# returns tuples of the 4 adjacent squares to p
def moveset(p):
    return [
        (p[0]+1, p[1]),
        (p[0]-1, p[1]),
        (p[0], p[1]+1),
        (p[0], p[1]-1),
    ]

def in_bounds(p, width, height):
    return 0 <= p[0] < width and 0 <= p[1] < height

def build_board(game_state: typing.Dict) -> typing.List[typing.List[str]]:
    board_width = game_state['board']['width']
    board_height = game_state['board']['height']

    self_length = len(game_state['you']['body'])
    self_head = text_to_tuple(game_state['you']['head'])

    can_die = set()
    can_kill = set()
    occupied = set()

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

# move is called on every turn and returns your next move
# Valid moves are "up", "down", "left", or "right"
# See https://docs.battlesnake.com/api/example-move for available data
def move(game_state: typing.Dict) -> typing.Dict:

    # load board state
    food, occupied, can_die, can_kill = build_board(game_state)

    is_move_safe = {"up": True, "down": True, "left": True, "right": True}

    # We've included code to prevent your Battlesnake from moving backwards
    my_head = game_state["you"]["body"][0]  # Coordinates of your head
    my_neck = game_state["you"]["body"][1]  # Coordinates of your "neck"

    if my_neck["x"] < my_head["x"]:  # Neck is left of head, don't move left
        is_move_safe["left"] = False

    elif my_neck["x"] > my_head["x"]:  # Neck is right of head, don't move right
        is_move_safe["right"] = False

    elif my_neck["y"] < my_head["y"]:  # Neck is below head, don't move down
        is_move_safe["down"] = False

    elif my_neck["y"] > my_head["y"]:  # Neck is above head, don't move up
        is_move_safe["up"] = False

    # TODO: Step 1 - Prevent your Battlesnake from moving out of bounds
    # board_width = game_state['board']['width']
    # board_height = game_state['board']['height']

    # TODO: Step 2 - Prevent your Battlesnake from colliding with itself
    # my_body = game_state['you']['body']

    # TODO: Step 3 - Prevent your Battlesnake from colliding with other Battlesnakes
    # opponents = game_state['board']['snakes']

    # Are there any safe moves left?
    safe_moves = []
    for move, isSafe in is_move_safe.items():
        if isSafe:
            safe_moves.append(move)

    if len(safe_moves) == 0:
        print(f"MOVE {game_state['turn']}: No safe moves detected! Moving down")
        return {"move": "down"}

    # Choose a random move from the safe ones
    next_move = random.choice(safe_moves)

    # TODO: Step 4 - Move towards food instead of random, to regain health and survive longer
    # food = game_state['board']['food']

    print(f"MOVE {game_state['turn']}: {next_move}")
    return {"move": next_move}


# Start server when `python main.py` is run
if __name__ == "__main__":
    from server import run_server

    run_server({"info": info, "start": start, "move": move, "end": end})
