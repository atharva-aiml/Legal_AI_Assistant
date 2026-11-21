from sqlalchemy import create_engine

from app.infrastructure.config import DATABASE_URL

# Schema owned by /database's Drizzle migrations (System Architecture §3) —
# this engine only reads/writes existing tables, never creates or alters
# them, mirroring Java's ddl-auto=validate posture.
#
# pool_pre_ping/pool_recycle: production Postgres (Neon) drops idle
# connections when its compute scales to zero after ~5 min. Without the ping,
# the first request after a quiet spell gets a dead pooled connection -> 500.
engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=240)
