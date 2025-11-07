from pathlib import Path


def _readme_text() -> str:
    readme_path = Path(__file__).resolve().parents[1] / "README.md"
    return readme_path.read_text(encoding="utf-8")


def test_web_dashboard_section_present():
    text = _readme_text()
    assert "## Web Dashboard" in text
    assert "FastAPI" in text
    assert "React + Vite" in text


def test_project_structure_documented():
    text = _readme_text()
    assert "backend/" in text and "frontend/" in text
    assert "docker-compose.yml" in text


def test_feature_table_includes_key_pages():
    text = _readme_text()
    assert "| Access Request | `/access-request`" in text
    assert "| Monitoring     | `/monitoring`" in text


def test_local_development_instructions_include_docker():
    text = _readme_text()
    assert "docker-compose up --build" in text
    assert "uvicorn backend.main:app" in text


def test_backend_and_frontend_examples_documented():
    text = _readme_text()
    assert "backend/api/access.py" in text
    assert "frontend/src/pages" in text
