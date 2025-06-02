import os


def env_bool(name: str) -> bool:
    return os.environ[name].lower() in ["1", "true"]
