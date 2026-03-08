"""Flask server wrapper exposing Battlesnake HTTP endpoints."""

import logging
import os
import typing

from flask import Flask
from flask import request


def run_server(handlers: typing.Dict):
    """Run the Battlesnake HTTP server with the provided lifecycle handlers."""
    app = Flask("Battlesnake")

    @app.get("/")
    def on_info():
        """Return Battlesnake metadata."""
        return handlers["info"]()

    @app.post("/start")
    def on_start():
        """Dispatch game start events."""
        game_state = request.get_json()
        handlers["start"](game_state)
        return "ok"

    @app.post("/move")
    def on_move():
        """Dispatch per-turn move requests."""
        game_state = request.get_json()
        return handlers["move"](game_state)

    @app.post("/end")
    def on_end():
        """Dispatch game end events."""
        game_state = request.get_json()
        handlers["end"](game_state)
        return "ok"

    @app.after_request
    def identify_server(response):
        """Attach a server identifier header for Battlesnake tooling."""
        response.headers.set(
            "server", "battlesnake/github/starter-snake-python"
        )
        return response

    host = "0.0.0.0"
    port = int(os.environ.get("PORT", "8000"))

    logging.getLogger("werkzeug").setLevel(logging.ERROR)

    print(f"\nRunning Battlesnake at http://{host}:{port}")
    app.run(host=host, port=port)
