import json
from types import SimpleNamespace
from pathlib import Path
import pytest
from kssolv_crew.models import JobRequest


def test_mp_selection(silicon, tmp_path, monkeypatch):
    import mp_api.client
    from kssolv_crew.materials import fetch_structure
    docs = [SimpleNamespace(material_id="mp-2", structure=silicon, energy_above_hull=.2, formula_pretty="Si"),
            SimpleNamespace(material_id="mp-1", structure=silicon, energy_above_hull=0, formula_pretty="Si")]
    class FakeMP:
        def __init__(self, **kwargs):
            self.materials = SimpleNamespace(summary=SimpleNamespace(search=lambda **kwargs: docs))
        def __enter__(self): return self
        def __exit__(self, *args): pass
    monkeypatch.setattr(mp_api.client, "MPRester", FakeMP)
    structure, metadata = fetch_structure("Si", None, "secret", tmp_path)
    assert metadata["material_id"] == "mp-1"
    assert structure == silicon
    with pytest.raises(ValueError, match="match"):
        fetch_structure("Al", "mp-1", "secret", tmp_path)


@pytest.mark.parametrize("mode,expected", [("prepare", "prepared"), ("run", "completed_unverified")])
def test_actual_crewai_flow_offline(silicon, tmp_path, monkeypatch, mode, expected):
    import kssolv_crew.workflow as workflow
    class Language:
        def __init__(self, *args): pass
        def normalize(self, text): return "Si"
        def report(self, facts): return "测试报告；未验证收敛。"
    monkeypatch.setattr(workflow, "LanguageAgents", Language)
    monkeypatch.setattr(workflow, "fetch_structure", lambda *a: (silicon, {"material_id": "mp-149"}))
    calls = []
    monkeypatch.setattr(workflow, "calculate", lambda *a: calls.append(True) or {"density_finite": True})
    req = JobRequest(task="硅能带", mp_api_key="private-mp", llm_api_key="private-llm", mode=mode)
    workflow.BandFlow(req, tmp_path, "unused", "unused").kickoff()
    assert json.loads((tmp_path / "status.json").read_text())["status"] == expected
    assert bool(calls) == (mode == "run")
    assert "未验证" in (tmp_path / "report.md").read_text(encoding="utf-8")
    assert not any("private-" in p.read_text(encoding="utf-8") for p in tmp_path.iterdir() if p.is_file())


def test_formula_agent_validates(monkeypatch):
    from kssolv_crew.agents import LanguageAgents
    from kssolv_crew.models import FormulaResult
    agent = LanguageAgents("not-used", "openai/not-used")
    monkeypatch.setattr(agent, "_call", lambda *args: FormulaResult(formula="Si"))
    assert agent.normalize("硅") == "Si"
    monkeypatch.setattr(agent, "_call", lambda *args: FormulaResult(formula="Qq999"))
    with pytest.raises(ValueError):
        agent.normalize("arbitrary")


def test_real_crew_objects_without_network(monkeypatch):
    from crewai import Crew
    from kssolv_crew.agents import LanguageAgents
    from kssolv_crew.models import FormulaResult
    captured = []
    def kickoff(crew, *args, **kwargs):
        captured.append(crew)
        return SimpleNamespace(pydantic=FormulaResult(formula="Si"), raw="Report from supplied facts")
    monkeypatch.setattr(Crew, "kickoff", kickoff)
    agent = LanguageAgents("fake-not-sent", "openai/gpt-4o-mini")
    assert agent.normalize("硅") == "Si"
    assert agent.report({"convergence_verified": False}).startswith("Report")
    assert len(captured) == 2
    assert all(not c.agents[0].tools and not c.agents[0].allow_delegation for c in captured)
