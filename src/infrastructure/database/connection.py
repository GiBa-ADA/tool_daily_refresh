import asyncio
import os
from typing import Optional

import asyncpg
import pandas as pd
from dotenv import load_dotenv

from src.config.settings import Config


class DatabaseClient:
    """ Handle database connection and query execution """

    def __init__(self, config: Config):
        load_dotenv()
        self.config = config
        self.username = os.getenv("DB_USERNAME")
        self.password = os.getenv("DB_PASSWORD")
        self.pool = None

        if not self.username or not self.password:
            raise ValueError("\033[91m[ERROR]\033[0m Missing DB_USERNAME or DB_PASSWORD in .env file")

    def _build_dsn(self, db_conf: dict) -> str:
        """Build PostgreSQL connection string"""
        return (
            f"postgresql://{self.username}:{self.password}"
            f"@{db_conf['host']}:{db_conf['port']}/{db_conf['database']}"
        )

    def _should_retry(self, error: Exception) -> bool:
        """Determine if error is retryable"""
        error_msg = str(error).lower()
        retryable_keywords = ["connection", "timeout", "network", "temporary"]
        return any(keyword in error_msg for keyword in retryable_keywords)
    
    async def init_pool(self, db_conf: dict):
        """Init connection pool"""
        if not self.pool:
            dsn = self._build_dsn(db_conf)

            self.pool = await asyncpg.create_pool(
                dsn=dsn,
                min_size=2,
                max_size=3,
                command_timeout=self.config.query_timeout
            )

    async def close_pool(self):
        if self.pool:
            await self.pool.close()
            self.pool = None

    async def fetch_query(
            self, 
            db_conf: dict,
            sql: str,
            seller_ids: list = None, 
            name: str = "",
            semaphore: asyncio.Semaphore = None
    ) -> Optional[pd.DataFrame]:
        """Fetch query using connection pool with seller_ids filter"""
        client = db_conf.get("client", "unknown")

        try:
            async with semaphore:
                for attempt in range(1, self.config.max_retries + 1):
                    try:
                        print(f"\033[94m[PROCESS]\033[0m [{name.replace('ecommerce_', '')}] Fetching data...")

                        async with self.pool.acquire() as conn:
                            # if seller_ids:
                            #     rows = await conn.fetch(sql, seller_ids)
                            # else:
                            #     rows = await conn.fetch(sql, client)
                            rows = await conn.fetch(sql, client)

                        if not rows:
                            print(f"\033[93m[WARNING]\033[0m [{name.replace('ecommerce_', '')}] No data returned")
                            return None

                        df = pd.DataFrame([dict(row) for row in rows])
                        df["client"] = client
                        df = df.dropna(axis=1, how="all")

                        print(f"\033[92m[SUCCESS]\033[0m [{name.replace('ecommerce_', '')}] → {len(df):,} rows fetched")
                        return df
                    
                    # %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
                    # CASE 1: Timeout connection...
                    # %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
                    except asyncio.TimeoutError:
                        print(f"\033[93m[WARNING]\033[0m  [{client}] Timeout on attempt {attempt}/{self.config.max_retries}")
                        if attempt >= self.config.max_retries:
                            raise Exception(f"\033[91m[ERROR]\033[0m Timeout after {self.config.max_retries} attempts")
                        await asyncio.sleep(2 ** attempt)

                    # %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
                    # CASE 2: Too many connection...
                    # %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
                    except asyncpg.TooManyConnectionsError:
                        print(
                            f"\033[93m[WARNING]\033[0m "
                            f"[{client}] Too many connections "
                            f"(attempt {attempt}/{self.config.max_retries})"
                        )

                        if attempt >= self.config.max_retries:
                            raise Exception(
                                f"\033[91m[ERROR]\033[0m "
                                f"Too many connections for {db_conf.get('host')}"
                            )

                        await asyncio.sleep(2 ** attempt)

                     # %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
                    # CASE 3: Replica recovery conflict...
                    # %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
                    except Exception as e:
                        error_msg = str(e)

                        is_recovery_conflict = (
                            "conflict with recovery" in error_msg
                            or "canceling statement due to conflict with recovery" in error_msg
                        )

                        if is_recovery_conflict:
                            if attempt >= self.config.max_retries:
                                raise Exception(
                                    f"\033[91m[ERROR]\033[0m "
                                    f"Failed to fetch data after retries: {error_msg}"
                                )

                            wait_time = 2 ** attempt

                            print(
                                f"\033[93m[WARNING]\033[0m "
                                f"[{client}] Replica recovery conflict. "
                                f"Retrying in {wait_time}s "
                                f"(attempt {attempt}/{self.config.max_retries})"
                            )

                            await asyncio.sleep(wait_time)
                            continue

                        if attempt >= self.config.max_retries or not self._should_retry(e):
                            raise Exception(
                                f"\033[91m[ERROR]\033[0m "
                                f"Failed to fetch data: {error_msg}"
                            )

                        wait_time = 2 ** attempt

                        print(
                            f"\033[93m[WARNING]\033[0m "
                            f"[{client}] Retrying in {wait_time}s: "
                            f"{error_msg[:100]}"
                        )

                        await asyncio.sleep(wait_time)

        except Exception as e:
            print(f"\033[91m[ERROR]\033[0m Query failed: {e}")
            return None
        
