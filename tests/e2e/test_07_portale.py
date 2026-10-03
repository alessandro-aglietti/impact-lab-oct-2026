"""Portale del Decisore sul DemoReplay: cinque passi, scarto con motivo, scarto considerato al passo 5."""

import threading

import pytest

from ambrogio.server import serve


@pytest.fixture
def portale_url():
    server = serve("127.0.0.1", 0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}/"
    server.shutdown()


def avanza(page):
    page.click("#avanza")
    page.wait_for_function("document.getElementById('status').textContent === ''")


def test_replay_scarto_e_passo_5(page, portale_url):
    errori = []
    page.on("pageerror", lambda e: errori.append(str(e)))
    page.goto(portale_url)
    page.wait_for_selector("#map path")
    assert page.locator("#map path").count() == 88

    avanza(page)
    assert page.locator(".item").count() == 2
    avanza(page)
    assert "S4" in page.locator("#notes").inner_text()

    page.locator(".item", has_text="tram").click()
    page.click("text=Scarta con motivo")
    assert "Scrivi il motivo" in page.locator("[role=alert]").inner_text()
    page.fill("#motivo", "tram ripristinato")
    page.click("text=Scarta con motivo")
    page.wait_for_selector(".decided")

    for _ in range(3):
        avanza(page)
    assert page.locator(".item", has_text="resta da verificare").count() == 0
    assert "B2" in page.locator("#notes").inner_text()
    assert page.locator("#avanza").is_disabled()
    assert errori == []
