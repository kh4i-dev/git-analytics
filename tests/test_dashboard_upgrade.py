import pytest
import re
import shutil
import subprocess
from collections.abc import Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401
from app.core.config import settings as global_settings
from app.core.security import encrypt_token
import os
import tempfile
from app.core.session import create_session_cookie
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models.user import User
from app.repositories import UserRepository, RepositoryRepository

@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    _, db_path = tempfile.mkstemp(suffix=".db")
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, class_=Session)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()
        try:
            if os.path.exists(db_path):
                os.unlink(db_path)
        except PermissionError:
            pass

def create_logged_in_user(db_session: Session) -> tuple[User, str]:
    encrypted_token = encrypt_token(
        "github-token",
        encryption_key=global_settings.encryption_key,
    )
    user = UserRepository(db_session).create(
        {
            "github_id": 1001,
            "github_login": "octo",
            "encrypted_github_token": encrypted_token,
        }
    )
    db_session.commit()
    return user, create_session_cookie(user.id)

def test_dashboard_redirects_unauthenticated() -> None:
    app = create_app()
    client = TestClient(app)
    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/login"

def test_global_dashboard_page_loads(db_session: Session) -> None:
    user, session_cookie = create_logged_in_user(db_session)
    app = create_app()
    
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session
        
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app, raise_server_exceptions=True)
    client.cookies.set("git_analytics_session", session_cookie)
    
    # Let's seed a repository to make sure listing repositories works
    repo_repo = RepositoryRepository(db_session)
    repo_repo.create({
        "user_id": user.id,
        "github_repo_id": 2001,
        "owner": "octo",
        "name": "super-project",
        "full_name": "octo/super-project",
        "is_private": False,
        "default_branch": "main",
        "html_url": "https://github.com/octo/super-project",
        "last_sync_status": "success",
    })
    db_session.commit()
    
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "Engineering Intelligence" in response.text
    assert "octo/super-project" in response.text
    assert "octo" in response.text  # Username in sidebar
    assert "Đăng Xuất" in response.text

def test_global_dashboard_script_parses() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is required for dashboard script parse check.")

    template = open("templates/dashboard_global.html", encoding="utf-8").read()
    match = re.search(
        r"{% block page_scripts %}\s*<script>([\s\S]*?)</script>\s*{% endblock %}",
        template,
    )
    assert match is not None
    script = match.group(1).replace(
        "let dashboardData = {{ stats | tojson }};",
        "let dashboardData = {};",
    )
    result = subprocess.run(
        [node, "--check", "-"],
        input=script,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_placeholder_pages(db_session: Session) -> None:
    user, session_cookie = create_logged_in_user(db_session)
    app = create_app()
    
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session
        
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    client.cookies.set("git_analytics_session", session_cookie)
    
    placeholders = [
        ("/settings", "Cài Đặt"),
        ("/account", "Tài Khoản"),
        ("/sync-status", "Trạng thái đồng bộ"),
        ("/developer-news", "Tin"),
        ("/ai-tools", "AI Workspace"),
    ]
    
    for route, expected_title in placeholders:
        response = client.get(route)
        assert response.status_code == 200
        assert expected_title in response.text

def test_repo_specific_dashboards(db_session: Session) -> None:
    user, session_cookie = create_logged_in_user(db_session)
    app = create_app()
    
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session
        
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    client.cookies.set("git_analytics_session", session_cookie)
    
    repo_repo = RepositoryRepository(db_session)
    repo = repo_repo.create({
        "user_id": user.id,
        "github_repo_id": 2001,
        "owner": "octo",
        "name": "super-project",
        "full_name": "octo/super-project",
        "is_private": False,
        "default_branch": "main",
        "html_url": "https://github.com/octo/super-project",
        "last_sync_status": "success",
    })
    db_session.commit()
    
    routes = [
        f"/dashboard/{repo.id}",
        f"/dashboard/{repo.id}/commits",
        f"/dashboard/{repo.id}/pull-requests",
        f"/dashboard/{repo.id}/issues",
        f"/dashboard/{repo.id}/insights",
    ]
    
    for route in routes:
        response = client.get(route)
        assert response.status_code == 200
        assert "super-project" in response.text
