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
        "author": "bs",  # TODO: Your Battlesnake Username
        "color": "#FFFFFF",  # TODO: Choose color
        "head": "default",  # TODO: Choose head
        "tail": "default",  # TODO: Choose tail
    }


# start is called when your Battlesnake begins a game
def start(game_state: typing.Dict):
    print("GAME START")


def chase_food(food, my_head, safe_moves):
    priority = ""

    # choose the food closest
    closestFood =  None #{ "x" : 4 * board_width, "y" : 4 *board_height}
    delta = { "x" : "", "y" : ""}



    for foodObj in food:

        
        if closestFood != None :
            closest = { "x" : closestFood["x"] - my_head["x"], "y" : closestFood["y"] - my_head["y"]} 

            delta["x"] = foodObj["x"] - my_head["x"]
            delta["y"] = foodObj["y"] - my_head["y"]
            

            if delta["x"] < delta["y"]:
                if abs(delta["x"]) < abs(closest["x"]):
                    closestFood = foodObj
            else:
                if abs(delta["y"]) < abs(closest["y"]):
                    closestFood = foodObj
        else:
            closestFood = foodObj



    delta = { "x" : closestFood["x"] - my_head["x"], "y" : closestFood["y"] - my_head["y"]} 


    if(closestFood != None):
        print(f"closestFood = {closestFood}, delta = {delta}")

        # check if in the same column
        if delta["x"] == 0:
            if delta["y"] > 0:
                priority = "up"
            else:
                priority = "down"
        # or if the same row
        elif delta["y"] == 0:
            if delta["x"] > 0:
                priority = "right"
            else:
                priority = "left"
        
        # otherwise, delta is the same
        else:
            if delta["x"] > 0:
                    priority = "right"
            else:
                    priority = "left"

    else:
        print("No available food")
    

    return priority





# end is called when your Battlesnake finishes a game
def end(game_state: typing.Dict):
    print("GAME OVER\n")

def lookAhead(snake):
    head = snake["body"][0]
    neck = snake["body"][1]

    lookRight = { "x" : (head["x"] + 1), "y" : head["y"] } 
    lookLeft = { "x" : (head["x"] - 1), "y" : head["y"] } 
    lookUp = { "x" : head["x"], "y" : (head["y"] + 1 )} 
    lookDown = { "x" : (head["x"]), "y" : (head["y"] - 1) }

    nextSteps = [lookRight, lookLeft, lookUp, lookDown]
    if neck in nextSteps:
       nextSteps.remove(neck)
    return nextSteps




    


# move is called on every turn and returns your next move
# Valid moves are "up", "down", "left", or "right"
# See https://docs.battlesnake.com/api/example-move for available data
def move(game_state: typing.Dict) -> typing.Dict:

    is_move_safe = {"up": True, "down": True, "left": True, "right": True}

    # We've included code to prevent your Battlesnake from moving backwards
    my_head = game_state["you"]["body"][0]  # Coordinates of your head
    my_neck = game_state["you"]["body"][1]  # Coordinates of your "neck"

    # TODO: Step 1 - Prevent your Battlesnake from moving out of bounds
    
    board_width = game_state["board"]["width"]
    board_height = game_state["board"]["height"]



    if my_head["x"] == (board_width - 1):
        is_move_safe["right"] = False
    elif my_head["x"] == 0:
        is_move_safe["left"] = False
 
         
    if my_head["y"] == (board_height - 1):
        is_move_safe["up"] = False
    elif my_head["y"] == 0:
        is_move_safe["down"] = False
    

    # TODO: Step 2 - Prevent your Battlesnake from colliding with itself
    my_body = game_state["you"]["body"]



    # TODO: Step 3 - Prevent your Battlesnake from colliding with other Battlesnakes
    snakes = game_state['board']['snakes']

    obstacles = my_body
    obstacles.remove(my_head)

    if my_body[-1] != my_body[-2]:
        obstacles.remove(my_body[-1])
    

    for snake in snakes:
        obstacles += snake["body"]
        if snake["body"][-1] != snake["body"][-2]:
            obstacles.remove(snake["body"][-1])


    lookRight = { "x" : (my_head["x"] + 1), "y" : my_head["y"] } 
    lookLeft = { "x" : (my_head["x"] - 1), "y" : my_head["y"] } 
    lookUp = { "x" : my_head["x"], "y" : (my_head["y"] + 1 )} 
    lookDown = { "x" : (my_head["x"]), "y" : (my_head["y"] - 1) } 

    
    

    myNextSteps = [lookRight, lookLeft, lookUp, lookDown]
    possibleKill = ""

    for snake in snakes:
        # list possible next moves for each snake
        for theirNextStep in lookAhead(snake):
            # check if they could possibly step into my space
            if theirNextStep in myNextSteps:
                # check if we are longer than them
                if game_state["you"]["length"] <= snake["length"]:
                    myNextSteps.remove(theirNextStep)
                else:
                    possibleKill = theirNextStep

    

    if lookUp in obstacles or lookUp not in myNextSteps:
        # print(f"Opponent detected Above")
        is_move_safe["up"] = False
    if lookDown in obstacles or lookDown not in myNextSteps:
        # print(f"Opponent detected below")
        is_move_safe["down"] = False
    if lookRight in obstacles or lookRight not in myNextSteps:
        # print(f"Opponent detected right")
        is_move_safe["right"] = False
    if lookLeft in obstacles or lookLeft not in myNextSteps:
        # print(f"Opponent detected left")
        is_move_safe["left"] = False

        



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
    # next_move = safe_moves[0]

    # TODO: Step 4 - Move towards food instead of random, to regain health and survive longer
    food = game_state['board']['food']

    if len(safe_moves) > 1:

        directMove = chase_food(food, my_head, safe_moves)

        print(f"most direct: {directMove} | Available safe moves: {safe_moves}")

        if (directMove != "") and (directMove in safe_moves):

            next_move = directMove    

        



    print(f"MOVE {game_state['turn']}: {next_move}") 
    # + {is_move_safe}")
    return {"move": next_move}


# Start server when `python main.py` is run
if __name__ == "__main__":
    from server import run_server

    run_server({"info": info, "start": start, "move": move, "end": end})
