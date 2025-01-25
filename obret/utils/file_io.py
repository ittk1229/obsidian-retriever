import pickle
from pathlib import Path


def load_pickle(filepath: str | Path):
    with open(filepath, "rb") as f:
        return pickle.load(f)


def save_pickle(data, filepath: str | Path):
    with open(filepath, "wb") as f:
        pickle.dump(data, f)
