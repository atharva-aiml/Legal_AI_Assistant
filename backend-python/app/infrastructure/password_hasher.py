import bcrypt

BCRYPT_COST = 12
# bcrypt only ever looks at the first 72 bytes of a password; bcrypt>=5
# refuses longer input outright rather than silently truncating it.
BCRYPT_MAX_PASSWORD_BYTES = 72


class PasswordTooLongError(ValueError):
    pass


class BcryptPasswordHasher:
    """Cost 12. Verifies every hash format already in the lawyers table —
    `$2b$` (the original Node `bcrypt` era) and `$2a$` (Spring's
    BCryptPasswordEncoder era) — so no existing password stops working."""

    def hash(self, raw_password: str) -> str:
        encoded = raw_password.encode("utf-8")
        if len(encoded) > BCRYPT_MAX_PASSWORD_BYTES:
            # The Java backend crashed with a 500 here; surfaced as a real validation error instead.
            raise PasswordTooLongError(f"A password can be at most {BCRYPT_MAX_PASSWORD_BYTES} bytes long.")
        return bcrypt.hashpw(encoded, bcrypt.gensalt(rounds=BCRYPT_COST)).decode("ascii")

    def matches(self, raw_password: str, password_hash: str) -> bool:
        try:
            return bcrypt.checkpw(raw_password.encode("utf-8"), password_hash.encode("utf-8"))
        except ValueError:
            # Malformed stored hash, or an over-long candidate password: never a match, never a 500.
            return False
