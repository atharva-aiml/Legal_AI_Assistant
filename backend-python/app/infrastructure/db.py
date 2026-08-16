from sqlalchemy import create_engine

from app.infrastructure.config import DATABASE_URL

# Schema owned by /database's Drizzle migrations (System Architecture §3) —
# this engine only reads/writes existing tables, never creates or alters
# them, mirroring Java's ddl-auto=validate posture.
engine = create_engine(DATABASE_URL)
