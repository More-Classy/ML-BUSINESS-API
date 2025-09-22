from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings
import aiomysql

# --------------------
# SQLAlchemy ORM Setup
# --------------------
engine = create_async_engine(
    f"mysql+aiomysql://{settings.MYSQL_USER}:{settings.MYSQL_PASSWORD}@"
    f"{settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DB}",
    echo=True,
    future=True
)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()

# Dependency for ORM
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# -----------------------------
# Raw SQL Connection Pool (aiomysql)
# -----------------------------
mysql_pool = None

async def create_mysql_pool():
    global mysql_pool
    if not mysql_pool:
        mysql_pool = await aiomysql.create_pool(
            host=settings.DATABASE_HOST,
            port=settings.DATABASE_PORT,
            user=settings.DATABASE_USER,
            password=settings.DATABASE_PASSWORD,
            db=settings.DATABASE_NAME,
            minsize=5,
            maxsize=20,
            autocommit=True
        )
    return mysql_pool

# async def get_mysql_connection():
#     global mysql_pool
#     if not mysql_pool:
#         await create_mysql_pool()
#     return mysql_pool
