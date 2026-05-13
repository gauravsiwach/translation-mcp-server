import asyncio
from db.session import AsyncSession
from db.models import Market, MarketLocale

MARKETS = [
    ("IN", "India", 34, ["en", "hi_IND"]),
    ("MX", "Mexico", 21, ["es_MX", "en"]),
    ("SA", "Saudi Arabia", 29, ["ar_SA", "en"]),
    ("EG", "Egypt", 30, ["ar_EG", "en"]),
    ("TR", "Turkey", 14, ["tr", "en"]),
    ("ES", "Spain", 13, ["es", "en", "zh"]),
    ("BR", "Brazil", 11, ["pt_BR", "en"]),
    ("PL", "Poland", 25, ["pl_PL", "en"]),
    ("TH", "Thailand", 24, ["th_TH", "en"]),
    ("RO", "Romania", 18, ["ro", "en"]),
    ("RU", "Russia", 15, ["ru", "en"]),
    ("PT", "Portugal", 16, ["pt", "en"]),
    ("CO", "Colombia", 7, ["es", "en"]),
    ("CL", "Chile", 22, ["es_CL", "en"]),
    ("AR", "Argentina", 28, ["es_AR", "en"]),
    ("DO", "Dominican Republic", 20, ["es_DO", "en"]),
    ("PE", "Peru", 32, ["es_PE", "en"]),
    ("EC", "Ecuador", 33, ["es_EC", "en"]),
    ("NZ", "New Zealand", 17, ["en"]),
    ("MXW", "Mexico Wholesaler", 26, ["es_MX", "en"]),
]

async def run():
    async with AsyncSession() as session:
        # Insert markets if not present
        for code, name, site_id, locales in MARKETS:
            existing = await session.execute(
                Market.__table__.select().where(Market.code == code)
            )
            row = existing.first()
            if not row:
                m = Market(code=code, name=name, site_id=site_id, is_active=True)
                session.add(m)
                await session.flush()
                for i, locale in enumerate(locales):
                    ml = MarketLocale(market_id=m.id, locale_code=locale, is_default=(i==0))
                    session.add(ml)
        await session.commit()

if __name__ == "__main__":
    asyncio.run(run())
