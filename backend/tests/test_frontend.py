from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.main import mount_frontend


def test_frontend_mount_serves_app_and_assets(tmp_path) -> None:
    assets = tmp_path / "assets"
    assets.mkdir()
    (tmp_path / "index.html").write_text("<html>SavorLoop</html>", encoding="utf-8")
    (assets / "app.js").write_text("window.savorLoop = true;", encoding="utf-8")
    app = FastAPI()
    mount_frontend(app, tmp_path)

    with TestClient(app) as client:
        page = client.get("/")
        script = client.get("/assets/app.js")

    assert page.status_code == 200
    assert "SavorLoop" in page.text
    assert script.status_code == 200
    assert script.text == "window.savorLoop = true;"
