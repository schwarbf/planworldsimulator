import re


def slug(name: str) -> str:
    """The name in lowercase letters, digits and dashes: what 'the same name' means."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


async def name_owner(sessions, title: str, exclude_id: str | None = None) -> str | None:
    """The id of an existing world with the same name (failed worlds do not count)."""
    from sqlalchemy import select

    from planworldsimulator_backend.db.models import World

    wanted = slug(title)
    async with sessions() as session:
        rows = await session.execute(
            select(World.id, World.title).where(World.status != "failed")
        )
    for world_id, other in rows:
        if world_id != exclude_id and slug(other) == wanted:
            return world_id
    return None
