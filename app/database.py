import asyncpg
from config import DB_URL

pool = None

async def connect_db():
    global pool
    pool = await asyncpg.create_pool(DB_URL)

async def disconnect_db():
    global pool
    if pool:
        await pool.close()

async def get_db_connection():
    if pool is None:
        raise Exception("Database pool is not initialized")
    return await pool.acquire()

async def release_db_connection(conn):
    if pool and conn:
        await pool.release(conn)
