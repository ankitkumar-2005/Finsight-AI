from contextlib import contextmanager

import mysql.connector
from mysql.connector.pooling import MySQLConnectionPool


_pool = None


def init_pool(config):
    global _pool
    if not config.get("DB_PASSWORD"):
        raise RuntimeError("MYSQL_PASSWORD is required. Copy backend/.env.example to backend/.env and configure MySQL.")
    _pool = MySQLConnectionPool(
        pool_name="finsight_pool",
        pool_size=5,
        pool_reset_session=True,
        host=config["DB_HOST"],
        port=config["DB_PORT"],
        database=config["DB_NAME"],
        user=config["DB_USER"],
        password=config["DB_PASSWORD"],
        autocommit=False,
        connection_timeout=5,
    )


def close_pool(_error=None):
    # mysql-connector releases checked-out connections when their request ends.
    return None


@contextmanager
def connection():
    if _pool is None:
        raise RuntimeError("Database connection pool has not been initialized.")
    conn = _pool.get_connection()
    try:
        yield conn
    finally:
        conn.close()
