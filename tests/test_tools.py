from types import SimpleNamespace

import tools


class FakeCompletions:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        content = self.outputs.pop(0) if self.outputs else ""
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=content)
                )
            ]
        )


class FakeClient:
    def __init__(self, outputs):
        self.chat = SimpleNamespace(completions=FakeCompletions(outputs))


def test_search_returns_results():
    results = tools.search_listings("vintage graphic tee", size=None, max_price=30)

    assert isinstance(results, list)
    assert len(results) > 0
    assert all(item["price"] <= 30 for item in results)


def test_search_empty_results():
    results = tools.search_listings("designer ballgown", size="XXS", max_price=5)

    assert results == []


def test_search_size_filter():
    results = tools.search_listings("graphic tee", size="L", max_price=30)

    assert len(results) > 0
    assert all("l" in item["size"].lower() or item["size"].lower() in "l" for item in results)


def test_suggest_outfit_empty_wardrobe_returns_general_advice(monkeypatch):
    fake_client = FakeClient(["Pair it with relaxed bottoms, clean sneakers, and a light layer for balance."])
    monkeypatch.setattr(tools, "_get_groq_client", lambda: fake_client)

    result = tools.suggest_outfit(
        {"title": "Graphic Tee", "price": 24, "category": "tops", "style_tags": ["vintage", "graphic tee"]},
        {"items": []},
    )

    assert "relaxed bottoms" in result
    assert fake_client.chat.completions.calls[0]["temperature"] == 0.7


def test_create_fit_card_blank_outfit_returns_error():
    result = tools.create_fit_card("   ", {"title": "Graphic Tee", "price": 24, "platform": "depop"})

    assert result == "Unable to create a fit card because the outfit suggestion is missing."


def test_create_fit_card_varies_across_calls(monkeypatch):
    fake_client = FakeClient([
        "First caption version for the fit card.",
        "Second caption version for the fit card.",
    ])
    monkeypatch.setattr(tools, "_get_groq_client", lambda: fake_client)

    item = {"title": "Graphic Tee", "price": 24, "platform": "depop"}
    outfit = "Graphic tee with baggy jeans and chunky sneakers."

    first = tools.create_fit_card(outfit, item)
    second = tools.create_fit_card(outfit, item)

    assert first != second
    assert fake_client.chat.completions.calls[0]["temperature"] == 1.0
    assert fake_client.chat.completions.calls[1]["temperature"] == 1.0