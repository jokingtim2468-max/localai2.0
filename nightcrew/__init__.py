"""Night Crew core: a local agent that runs on open models (Ollama / llama.cpp / MLX).

Front-end agnostic. The Flask server (server.py) and the Eclipse desktop app both drive
`agent.run_turn()`, which yields events: token, thinking, tool_call, tool_result,
approval, error, done.
"""
__version__ = "2.0.0"
