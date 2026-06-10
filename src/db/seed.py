import asyncio
from sqlalchemy import text
from db.session import AsyncSession

async def seed_languages():
    """Insert default languages if they don't exist"""
    async with AsyncSession() as session:
        default_languages = [
            {"code": "en", "language": "English"},
            {"code": "hi_IND", "language": "Hindi (India)"},
        ]
        for lang_data in default_languages:
            existing = await session.execute(
                text("SELECT language_code FROM customer_uat_ind.pepsi_languages WHERE language_code = :code"),
                {"code": lang_data["code"]}
            )
            if not existing.first():
                await session.execute(
                    text("INSERT INTO customer_uat_ind.pepsi_languages (language_code, language) VALUES (:code, :language)"),
                    lang_data
                )
        await session.commit()
        print("Default languages seeded successfully.")

async def run():
    await seed_languages()

if __name__ == "__main__":
    asyncio.run(run())

