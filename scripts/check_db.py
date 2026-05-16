import asyncio
from sqlalchemy import text
from db import session as db_session

async def main():
    if db_session.engine is None:
        print("No DB engine configured. Set DB_URL in .env and restart.")
        return

    async with db_session.engine.connect() as conn:
        try:
            res = await conn.execute(text("SELECT count(*) FROM customer_uat_ind.pepsi_languages"))
            print("pepsi_languages:", res.scalar_one())
        except Exception as e:
            print("pepsi_languages query failed:", str(e))

        try:
            res = await conn.execute(text("SELECT count(*) FROM customer_uat_ind.pepsi_translations"))
            print("pepsi_translations:", res.scalar_one())
        except Exception as e:
            print("pepsi_translations query failed:", str(e))

if __name__ == '__main__':
    asyncio.run(main())
