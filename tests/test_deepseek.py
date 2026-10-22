from types import SimpleNamespace
import pytest


def test_deepseek_short_name_uses_budgeted_provider():
    from kssolv_crew.agents import LanguageAgents
    agents = LanguageAgents("fake-key", " deepseek ")
    assert agents.model == "deepseek/deepseek-flash"
    assert agents.budget.limit == 2


@pytest.mark.parametrize("model", ["", "unknown", "deepseek/", "/model"])
def test_incomplete_model_rejected_without_api(model):
    from kssolv_crew.models import normalize_llm_model
    with pytest.raises(ValueError, match="LLM"):
        normalize_llm_model(model)


def test_crewai_deepseek_two_call_budget_and_caps(monkeypatch):
    from kssolv_crew.agents import LanguageAgents
    import kssolv_crew.deepseek as module
    requests = []
    class Client:
        def __init__(self, **kwargs):
            assert kwargs["follow_redirects"] is False
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, url, headers, json):
            requests.append(json)
            content = '{"formula":"Si"}' if len(requests) == 1 else '计算返回，参数收敛仍待核验。'
            return SimpleNamespace(status_code=200, json=lambda: {
                "choices": [{"message": {"content": content}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5}})
    monkeypatch.setattr(module.httpx, "Client", Client)
    agents = LanguageAgents("fake-private-key", "deepseek/deepseek-flash")
    assert agents.normalize("计算硅能带") == "Si"
    assert "收敛" in agents.report({"scf_converged": True})
    assert agents.budget.attempted == 2
    assert [r["max_tokens"] for r in requests] == [192, 600]
    assert all(r["thinking"]["type"] == "disabled" for r in requests)
    with pytest.raises(RuntimeError, match="budget"):
        agents.budget.claim()
    assert len(requests) == 2
