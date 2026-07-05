from __future__ import annotations

from logger import configure_logging
from settings import Settings


def main() -> None:
    """Initialize the minimal POC runtime."""
    settings = Settings.load()
    logger = configure_logging(settings)

    print("====================================")
    print("VisualCron AI Agent")
    print("POC Started Successfully")
    print("====================================")

    logger.info("POC startup completed")


if __name__ == "__main__":
    main()
