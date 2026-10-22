import json
from pathlib import Path
from crewai.flow.flow import Flow, listen, start
from .agents import LanguageAgents
from .convert import prepare
from .engine import calculate
from .materials import fetch_structure
from .storage import stage


class BandFlow(Flow):
    def __init__(self, request, output, root, model, engine_session=None):
        super().__init__()
        self.request, self.output, self.root = request, Path(output), root
        self._engine_session = engine_session
        self.language = LanguageAgents(request.llm_api_key.get_secret_value(), model)

    @start()
    def normalize(self):
        stage(self.output, "normalizing")
        return self.language.normalize(self.request.task)

    @listen(normalize)
    def structure(self, formula):
        stage(self.output, "fetching_structure")
        structure, self.metadata = fetch_structure(formula, self.request.material_id,
            self.request.mp_api_key.get_secret_value(), self.output)
        return structure

    @listen(structure)
    def convert(self, structure):
        stage(self.output, "preparing")
        self.config = prepare(structure, self.request.parameters, self.output)
        return self.config

    @listen(convert)
    def compute(self, config):
        if self.request.mode == "prepare":
            return {"status": "prepared_only", "convergence_verified": False,
                    "note": "MATLAB SCF/NSCF not executed"}
        stage(self.output, "calculating")
        return calculate(self.root, self.output, session=self._engine_session) if self._engine_session is not None else calculate(self.root, self.output)

    @listen(compute)
    def report(self, result):
        stage(self.output, "reporting")
        plots = sorted(p.name for p in self.output.glob("band_*.png"))
        facts = {"material": self.metadata, "config": self.config, "calculation": result, "band_plots": plots,
                 "limits": ["No numerical band gap extraction", "Cutoff and k-mesh convergence not certified",
                            "Default parameters are examples, not converged scientific settings"]}
        (self.output / "facts.json").write_text(json.dumps(facts, ensure_ascii=False, indent=2), encoding="utf-8")
        # A deterministic facts report survives an unavailable report LLM.
        baseline = "# KSSOLV 任务报告\n\n状态：" + result.get("status", "计算返回；收敛未验证")
        if result.get("scf_converged"):
            scf = result.get("scf", {})
            baseline += f"\n\nSCF 达到程序阈值：{scf.get('iterations')} 次迭代，最终残差 {scf.get('final_residual')}。"
        baseline += "\n\n未提取数值带隙；截断能、k 网格和带数尚未做系统收敛测试。\n\n详见 facts.json、MATLAB 日志和能带图。\n"
        for plot in plots:
            baseline += f"\n![{plot}]({plot})\n"
        (self.output / "report.md").write_text(baseline, encoding="utf-8")
        try:
            narrative = self.language.report(facts)
            (self.output / "report.md").write_text(baseline + "\n## LLM 辅助说明（需核对）\n\n" + narrative, encoding="utf-8")
        except Exception:
            stage(self.output, "reporting", warning="report_llm_failed; deterministic report retained")
        from .reporting import export_html
        export_html(self.output)
        stage(self.output, "prepared" if self.request.mode == "prepare" else "completed_unverified")
        return facts
