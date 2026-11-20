from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from sqlalchemy.engine import Connection

from app.infrastructure.db import engine

# The connection of the transaction currently open in this request/thread, if
# any. Repositories join it instead of opening their own, which is how
# MatterService/ClientService.delete_cascade get all-or-nothing semantics
# across several repositories (the former Java @Transactional). Outside such a
# block every repository call is its own short transaction, exactly as each
# Spring Data save() was.
_current: ContextVar[Connection | None] = ContextVar("crud_transaction", default=None)


@contextmanager
def connection() -> Iterator[Connection]:
    conn = _current.get()
    if conn is not None:
        yield conn
        return
    with engine.begin() as conn:
        yield conn


class SqlUnitOfWork:
    @contextmanager
    def transaction(self) -> Iterator[None]:
        if _current.get() is not None:  # nested: join the outer transaction
            yield
            return
        with engine.begin() as conn:
            token = _current.set(conn)
            try:
                yield
            finally:
                _current.reset(token)
