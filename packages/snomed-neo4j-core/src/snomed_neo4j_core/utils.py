import os


def env_bool(name: str) -> bool:
    return os.environ[name].lower() in ["1", "true"]


def optional_env_int(name: str) -> int | None:
    value = os.getenv(name)
    return None if value is None else int(value)
