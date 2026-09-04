import os
import pickle


def run(args: list[str]) -> int:
    with open(args[0], "wb") as f:
        pickle.dump(dict(os.environ), f)
    return 0
