from fluxmed.security.passwords import hash_password, password_needs_rehash, verify_password


def test_argon2id_password_round_trip() -> None:
    password_hash = hash_password("StrongPassword123!")

    assert password_hash.startswith("$argon2id$")
    assert verify_password("StrongPassword123!", password_hash)
    assert not verify_password("wrong-password", password_hash)
    assert not password_needs_rehash(password_hash)


def test_short_password_is_rejected_for_hashing() -> None:
    try:
        hash_password("short")
    except ValueError as exc:
        assert "8 characters" in str(exc)
    else:
        raise AssertionError("Expected short password to be rejected")
