"""
CLI entry point for the agentic music recommender.

Usage:
    # Pass the request as command-line arguments:
    python -m src.agent_main I want something calm to study to

    # Or run interactively (prompts for input):
    python -m src.agent_main
"""

import sys
from .agent import run_agent


def main() -> None:
    if len(sys.argv) > 1:
        user_text = " ".join(sys.argv[1:]).strip()
    else:
        try:
            user_text = input("Describe what you want to listen to: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nNo input provided.", file=sys.stderr)
            sys.exit(1)

    if not user_text:
        print("Error: Please describe the music you want.", file=sys.stderr)
        sys.exit(1)

    run_agent(user_text)


if __name__ == "__main__":
    main()
