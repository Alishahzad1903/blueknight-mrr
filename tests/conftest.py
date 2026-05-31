import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text

from app.main import app
from app.db import SessionLocal
from app.auth.jwt_helper import encode_token
from app.llm.in_memory import InMemoryLLMClient
from app.dependencies import get_llm_client


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def db_session():
    async with SessionLocal() as session:
        yield session


@pytest.fixture
def auth_header():
    def _make(user_id: int, org_id: int = 1):
        return {"Authorization": f"Bearer {encode_token(user_id, org_id)}"}
    return _make


@pytest.fixture
def llm():
    stub = InMemoryLLMClient()
    app.dependency_overrides[get_llm_client] = lambda: stub
    yield stub
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(autouse=True)
async def reset_db():
    """Truncate volatile tables and reset section versions before every test."""
    async with SessionLocal() as s:
        try:
            await s.execute(text("DELETE FROM report_shares"))
            await s.execute(text("DELETE FROM report_section_edits"))
            await s.execute(text(
                "UPDATE report_sections SET version = 1, "
                "content = '{\"text\": \"original\"}'::jsonb "
                "WHERE report_id = 1"
            ))
            await s.commit()
        except Exception:
            await s.rollback()
    yield
