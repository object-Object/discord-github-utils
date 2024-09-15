import os
import sys
import traceback

import httpx


def main():
    if (url := os.getenv("HEALTH_CHECK_URL")) is None:
        raise ValueError("Environment variable not set: HEALTH_CHECK_URL")
    httpx.get(url).raise_for_status()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
