from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import async_sessionmaker

from planworldsimulator_backend.db.models import World

# Curated worlds shown first in the public catalogue. The website has matching
# preview images; the world folders arrive with the real template.
FEATURED = [
    {
        "id": "fission-ops",
        "name": "Fission Ops",
        "seed": 3141,
        "premise": "Keep a reactor safe through heat waves and shift shortages.",
        "prompt": (
            "A nuclear power plant control room. Deliver 1 GW to the city for 90 "
            "days while keeping the core below 650 °C and every shift staffed."
        ),
    },
    {
        "id": "bike-factory",
        "name": "Bike Factory",
        "seed": 4821,
        "premise": "Run a supply chain from tier-2 suppliers to three stores.",
        "prompt": (
            "A bike factory supply chain with tier 1 and tier 2 suppliers, a "
            "warehouse, an assembly plant and three stores."
        ),
    },
    {
        "id": "grid-juggler",
        "name": "Grid Juggler",
        "seed": 2718,
        "premise": "Balance a city's power grid as supply and demand shift.",
        "prompt": (
            "A city power grid with solar, wind and gas plants and a battery. "
            "Keep the lights on at the lowest cost."
        ),
    },
    {
        "id": "seven-seas",
        "name": "Seven Seas",
        "seed": 1618,
        "premise": "Route cargo ships across ports with storms and shifting prices.",
        "prompt": (
            "A shipping network across seven seas. Route cargo between ports to "
            "maximize profit while storms close lanes."
        ),
    },
]


async def seed_featured(sessions: async_sessionmaker) -> None:
    """Insert the curated worlds once. Safe to call on every startup."""
    base = datetime.now(UTC)
    async with sessions() as session:
        for i, item in enumerate(FEATURED):
            if await session.get(World, item["id"]) is not None:
                continue
            session.add(
                World(
                    id=item["id"],
                    title=item["name"],
                    prompt=item["prompt"],
                    seed=item["seed"],
                    status="ready",
                    storyline=item["premise"],
                    featured=True,
                    created_at=base - timedelta(seconds=i),
                    updated_at=base,
                )
            )
        await session.commit()
