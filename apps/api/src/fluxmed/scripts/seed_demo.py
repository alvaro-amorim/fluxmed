import os

from fluxmed.city.persistence import seed_santa_aurora
from fluxmed.domain.enums import UserRole
from fluxmed.infrastructure.database import session_scope
from fluxmed.infrastructure.models.user import UserModel
from fluxmed.infrastructure.repositories import UserRepository
from fluxmed.security.passwords import hash_password

DEFAULT_DEMO_EMAIL = "planner@fluxmed.demo"
DEFAULT_DEMO_DISPLAY_NAME = "Planejador Demo"
DEFAULT_DEMO_PASSWORD = "FluxMedDemo2026!"


def seed_demo_user() -> UserModel:
    email = os.getenv("DEMO_PLANNER_EMAIL", DEFAULT_DEMO_EMAIL).strip().lower()
    display_name = os.getenv("DEMO_PLANNER_DISPLAY_NAME", DEFAULT_DEMO_DISPLAY_NAME).strip()
    password = os.getenv("DEMO_PLANNER_PASSWORD", DEFAULT_DEMO_PASSWORD)

    with session_scope() as session:
        users = UserRepository(session)
        user = users.get_by_email(email)
        if user is None:
            user = UserModel(
                email=email,
                display_name=display_name,
                password_hash=hash_password(password),
                role=UserRole.PLANNER,
                active=True,
            )
            users.add(user)
        else:
            user.display_name = display_name
            user.password_hash = hash_password(password)
            user.role = UserRole.PLANNER
            user.active = True
        session.flush()
        user_id = user.id

    with session_scope() as session:
        persisted = session.get(UserModel, user_id)
        if persisted is None:
            raise RuntimeError("Demo user could not be persisted")
        return persisted


def main() -> None:
    user = seed_demo_user()
    with session_scope() as session:
        city = seed_santa_aurora(session)
        city_name = city.name
    print(f"Demo planner ready: {user.email}")
    print(f"Demo city ready: {city_name}")


if __name__ == "__main__":
    main()
