import os
import ssl
import asyncio
import asyncpg
from asyncpg.pool import Pool
from utils.logs.pretty_log import pretty_log
from dotenv import load_dotenv

load_dotenv()


# -------------------- [💙 SAFE POOL WRAPPER WITH RETRY] --------------------
class SafePool:
    def __init__(
        self,
        dsn: str,
        ssl_context: ssl.SSLContext = None,
        min_size=1,
        max_size=10,
        retry_count=3,
    ):
        self.dsn = dsn
        self.ssl_context = ssl_context
        self.min_size = min_size
        self.max_size = max_size
        self.retry_count = retry_count
        self._pool: Pool | None = None

    async def connect(self):
        self._pool = await asyncpg.create_pool(
            dsn=self.dsn,
            ssl=self.ssl_context,
            min_size=self.min_size,
            max_size=self.max_size,
        )

    def acquire(self):
        if not self._pool:
            raise RuntimeError("SafePool not connected. Call connect() first.")
        return SafeConnection(self._pool)

    async def _retry(self, method, *args, **kwargs):
        last_exc = None
        for attempt in range(1, self.retry_count + 2):
            try:
                async with self.acquire() as conn:
                    return await method(conn, *args, **kwargs)
            except (
                asyncpg.exceptions.ConnectionDoesNotExistError,
                ConnectionResetError,
                OSError,
                asyncio.TimeoutError,  # <— added
            ) as e:
                last_exc = e
                pretty_log(
                    tag="warn",
                    message=f"[Retry {attempt}/{self.retry_count + 1}] {method.__name__} failed: {e}. Reconnecting...",
                    include_trace=False,
                )
                await asyncio.sleep(0.5)
                await self._reconnect()
        raise last_exc

    async def _reconnect(self):
        if self._pool:
            try:
                await self._pool.close()
            except Exception:
                pass
        self._pool = await asyncpg.create_pool(
            dsn=self.dsn,
            ssl=self.ssl_context,
            min_size=self.min_size,
            max_size=self.max_size,
        )

    async def fetch(self, *args, **kwargs):
        return await self._retry(
            lambda conn, *a, **k: conn.fetch(*a, **k), *args, **kwargs
        )

    async def fetchrow(self, *args, **kwargs):
        return await self._retry(
            lambda conn, *a, **k: conn.fetchrow(*a, **k), *args, **kwargs
        )

    async def execute(self, *args, **kwargs):
        return await self._retry(
            lambda conn, *a, **k: conn.execute(*a, **k), *args, **kwargs
        )

    async def fetchval(self, *args, **kwargs):
        row = await self.fetchrow(*args, **kwargs)
        return row[0] if row else None


# -------------------- [💜 SAFE CONNECTION CONTEXT] --------------------
class SafeConnection:
    def __init__(self, pool: Pool):
        self.pool = pool
        self.conn = None

    async def __aenter__(self):
        self.conn = await self.pool.acquire()
        return self.conn

    async def __aexit__(self, exc_type, exc, tb):
        try:
            if self.conn:
                await self.pool.release(self.conn)
        except Exception:
            pass


# -------------------- [💧 GET PG POOL] --------------------
async def get_pg_pool():
    internal_url = os.getenv("DATABASE_URL")
    public_url = os.getenv("DATABASE_PUBLIC_URL")

    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    # Try internal URL first
    try:
        pool = SafePool(dsn=internal_url, ssl_context=ssl_context)
        await pool.connect()
        pretty_log(tag="db", message="Connected to Postgres via internal URL!")
        return pool
    except Exception as e:
        pretty_log(
            tag="info",
            message=f"Internal URL failed to connect: {e}",
            include_trace=True,
        )

    # Try public URL fallback
    try:
        pool = SafePool(dsn=public_url, ssl_context=ssl_context, retry_count=5)
        await pool.connect()
        pretty_log(tag="db", message="Connected to Postgres via public URL!")
        return pool
    except Exception as e:
        pretty_log(
            tag="critical",
            message=f"Public URL failed to connect: {e}",
            include_trace=True,
        )

    # Both failed
    pretty_log(
        tag="critical",
        message="Could not connect to either internal or public Postgres database.",
        include_trace=True,
    )
    raise ConnectionError(
        "💖 Could not connect to either internal or public Postgres database. Sending cozy vibes!"
    )
