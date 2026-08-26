"""One-off production bootstrap command: seed the first editable event and admin."""

from __future__ import annotations

import argparse
import asyncio

from app.core.config import get_settings
from app.db.session import AsyncSessionLocal, engine
from app.services.seed import seed_demo_data


async def bootstrap(seed: bool) -> None:
    settings = get_settings().model_copy(update={"seed_demo_data": seed})
    if seed:
        async with AsyncSessionLocal() as session:
            await seed_demo_data(session, settings)
        print("Initial event and administrator are ready.")
    await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare FLIPBELT initial activity data")
    parser.add_argument("--seed", action="store_true", help="Create initial event and administrator only when absent")
    args = parser.parse_args()
    asyncio.run(bootstrap(seed=args.seed))


if __name__ == "__main__":
    main()
