#!/usr/bin/env python3
"""
Re-seed default card templates into the database.
Usage: python scripts/seed_templates.py
"""
import os
import sys
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.engine import init_db, get_session
from database.repository import seed_default_templates


async def main():
    await init_db()
    async with get_session() as session:
        await seed_default_templates(session)
        await session.commit()
    print("✅ Default templates seeded.")


if __name__ == "__main__":
    asyncio.run(main())