"""Tk desktop frontend: direct worker execution, no localhost connection."""
import argparse
import os
from pathlib import Path
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText
from pydantic import ValidationError
from .config import resolve_kssolv
from .desktop_runner import DesktopRunner, STATUS_LABELS, history, read_json
from .models import JobRequest, Parameters, normalize_llm_model

TITLE = "KSSOLV 材料能带计算"


class DesktopApp:
    def __init__(self, window, project):
        self.window, self.project = window, Path(project).resolve()
        self.runner = DesktopRunner(self.project)
        self.selected = None
        self._closing = False
        self._report_signature = None
        self.image = None
        self.cancel_error = None
        window.title(TITLE)
        window.geometry("1080x800")
        window.minsize(900, 650)
        window.protocol("WM_DELETE_WINDOW", self.close)
        style = ttk.Style(window)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("TLabel", font=("Microsoft YaHei UI", 10))
        style.configure("TButton", font=("Microsoft YaHei UI", 10), padding=(10, 5))
        style.configure("Title.TLabel", font=("Microsoft YaHei UI", 18, "bold"))
        outer = ttk.Frame(window, padding=16)
        outer.pack(fill="both", expand=True)
        header = ttk.Frame(outer)
        header.pack(fill="x", pady=(0, 12))
        ttk.Label(header, text=TITLE, style="Title.TLabel").pack(side="left")
        ttk.Button(header, text="简易教程", command=self.show_help).pack(side="right")

        form = ttk.LabelFrame(outer, text="新任务", padding=10)
        form.pack(fill="x")
        form.columnconfigure(1, weight=1)
        form.columnconfigure(3, weight=1)
        ttk.Label(form, text="材料任务").grid(row=0, column=0, sticky="nw", padx=(0, 8))
        self.task = tk.Text(form, height=2, font=("Microsoft YaHei UI", 10), wrap="word")
        self.task.insert("1.0", "计算硅 Si 的能带图")
        self.task.grid(row=0, column=1, columnspan=3, sticky="ew", pady=(0, 8))
        self.mp_key, self.llm_key = tk.StringVar(), tk.StringVar()
        self._field(form, "MP API Key", self.mp_key, 1, 0, secret=True)
        self._field(form, "LLM API Key", self.llm_key, 1, 2, secret=True)
        self.material_id = tk.StringVar(value="mp-149")
        self._field(form, "MP ID（可选）", self.material_id, 2, 0)
        ttk.Label(form, text="任务模式").grid(row=2, column=2, sticky="w", padx=(12, 8))
        self.mode = tk.StringVar(value="只生成输入文件")
        ttk.Combobox(form, textvariable=self.mode, values=["只生成输入文件", "执行 MATLAB 计算"], state="readonly").grid(row=2, column=3, sticky="ew", pady=4)

        advanced = ttk.Frame(form)
        advanced.grid(row=3, column=0, columnspan=4, sticky="ew", pady=(6, 0))
        self.ecut, self.nbnd, self.mesh, self.points = (tk.StringVar(value=x) for x in ["20", "14", "2 2 2", "20"])
        for col, (label, var, width) in enumerate([("ecut", self.ecut, 7), ("nbnd", self.nbnd, 7),
                ("SCF 网格", self.mesh, 11), ("每段 k 点", self.points, 7)]):
            ttk.Label(advanced, text=label).grid(row=0, column=2*col, padx=(0 if col == 0 else 15, 5))
            ttk.Entry(advanced, textvariable=var, width=width).grid(row=0, column=2*col+1)
        self.model = tk.StringVar(value=os.environ.get("KSSOLV_LLM_MODEL", "openai/gpt-4o-mini"))
        self._field(form, "LLM 模型", self.model, 4, 0)
        ttk.Label(form, text="泛函 PBE · Gaussian 展宽 · 参数需做收敛测试", foreground="#64748b").grid(row=4, column=2, columnspan=2, sticky="w", padx=12)

        actions = ttk.Frame(outer)
        actions.pack(fill="x", pady=10)
        self.start_button = ttk.Button(actions, text="开始任务", command=self.start)
        self.start_button.pack(side="left")
        self.cancel_button = ttk.Button(actions, text="停止当前任务", command=self.cancel, state="disabled")
        self.cancel_button.pack(side="left", padx=8)
        ttk.Button(actions, text="打开结果目录", command=self.open_output).pack(side="left")
        ttk.Button(actions, text="打开图文报告", command=self.open_report).pack(side="left", padx=8)
        ttk.Button(actions, text="刷新历史", command=self.refresh_history).pack(side="left", padx=8)
        self.progress = ttk.Progressbar(actions, mode="indeterminate", length=110)
        self.progress.pack(side="right")
        self.status = tk.StringVar(value="就绪：先填写两种 API 密钥，建议先生成输入文件。")
        ttk.Label(outer, textvariable=self.status, wraplength=1000).pack(anchor="w", pady=(0, 8))

        panes = ttk.Panedwindow(outer, orient="horizontal")
        panes.pack(fill="both", expand=True)
        left = ttk.Frame(panes)
        right = ttk.Notebook(panes)
        panes.add(left, weight=1)
        panes.add(right, weight=3)
        ttk.Label(left, text="任务历史（最近 200 项）").pack(anchor="w", pady=(0, 5))
        self.jobs = ttk.Treeview(left, columns=("material", "state"), show="headings", selectmode="browse", height=9)
        self.jobs.heading("material", text="材料 / 任务")
        self.jobs.heading("state", text="状态")
        self.jobs.column("material", width=95, minwidth=70)
        self.jobs.column("state", width=155, minwidth=100)
        self.jobs.pack(fill="both", expand=True)
        self.jobs.bind("<<TreeviewSelect>>", self.select_job)
        self.report = self._text_tab(right, "报告")
        self.logs = self._text_tab(right, "日志")
        image_tab = ttk.Frame(right, padding=8)
        right.add(image_tab, text="能带图")
        self.plot_choice = tk.StringVar()
        self.plot_list = ttk.Combobox(image_tab, textvariable=self.plot_choice, state="readonly")
        self.plot_list.pack(fill="x")
        self.plot_list.bind("<<ComboboxSelected>>", lambda e: self.show_plot())
        self.plot_label = ttk.Label(image_tab, text="计算完成后可在此查看各段能带图。", anchor="center")
        self.plot_label.pack(fill="both", expand=True, pady=8)
        ttk.Label(outer, text="密钥仅保存在本次会话内存中，不写入配置。计算返回不等于收敛已验证。", foreground="#64748b").pack(anchor="w", pady=(9, 0))
        self.refresh_history()
        window.after(500, self.tick)

    def _field(self, parent, label, variable, row, column, secret=False):
        ttk.Label(parent, text=label).grid(row=row, column=column, sticky="w", padx=(0 if column == 0 else 12, 8))
        ttk.Entry(parent, textvariable=variable, show="●" if secret else "", width=27).grid(row=row, column=column+1, sticky="ew", pady=4)

    def _text_tab(self, notebook, title):
        box = ScrolledText(notebook, wrap="word", font=("Microsoft YaHei UI", 10), state="disabled", padx=10, pady=8)
        notebook.add(box, text=title)
        return box

    @staticmethod
    def set_text(widget, value):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", value)
        widget.configure(state="disabled")

    def show_help(self):
        if getattr(self, "help_window", None) is not None and self.help_window.winfo_exists():
            self.help_window.lift()
            return
        dialog = self.help_window = tk.Toplevel(self.window)
        dialog.title("简易教程")
        dialog.geometry("690x610")
        dialog.transient(self.window)
        content = ScrolledText(dialog, wrap="word", font=("Microsoft YaHei UI", 11), padx=18, pady=15)
        content.pack(fill="both", expand=True)
        root = resolve_kssolv(project=self.project)
        detected = "已检测到" if root.is_dir() else "未检测到"
        text = f"""首次使用

1. 安装 Python 3.12（含 Tcl/Tk）和已激活的完整 MATLAB；已验证 MATLAB R2025b。解压软件后运行 install.cmd，看到 Installation completed 再运行 start.cmd。

2. 填写自己的 MP 和 LLM API 密钥。DeepSeek 用户在模型栏填写 deepseek/deepseek-flash（也支持简写 deepseek）。密钥不会自动保存。

3. 输入材料任务，例如“计算硅 Si 的能带图”。首次可保留 MP ID mp-149；更换材料时请修改或清空此 ID。同一化学式可能有多个结构，可用 MP ID 指定目标。

4. “只生成输入文件”不运行 MATLAB。需要能带图时选择“执行 MATLAB 计算”，保留示例参数开始任务，等待完成。MATLAB 在后台运行，看不到 MATLAB 主窗口是正常的。

5. 从历史列表选择任务，点击“打开图文报告”查看全部图片。结果目录里的 report.html 可独立分享，或用浏览器打印为 PDF。旧任务也支持生成报告，无需重算。

6. 停止计算使用“停止当前任务”。失败时查看日志；默认参数仅供测试，SCF 收敛不等于截断能、网格、带数已经完成系统收敛验证。

KSSOLV 自动检测

完整发布包包含 kssolv-3o-dev，无需手动选择。软件自动查找项目内部或与项目同级的该文件夹。源码包可能不含 KSSOLV，需自行补齐完整目录。

当前检测：{detected}
{root}

联网与费用

获取材料和调用语言模型需要联网。DeepSeek 每次任务最多两次请求，重新提交会重新请求。无需为了查看报告重新计算。

详细安装说明位于项目 docs/INSTALL.md。
"""
        self.set_text(content, text)
        ttk.Button(dialog, text="关闭", command=dialog.destroy).pack(pady=8)

    def start(self):
        try:
            model = normalize_llm_model(self.model.get())
            self.model.set(model)
            request = JobRequest(task=self.task.get("1.0", "end").strip(),
                mp_api_key=self.mp_key.get().strip(), llm_api_key=self.llm_key.get().strip(),
                material_id=self.material_id.get().strip() or None,
                mode="prepare" if self.mode.get() == "只生成输入文件" else "run",
                parameters=Parameters(ecut=float(self.ecut.get()), nbnd=int(self.nbnd.get()),
                    mesh=tuple(int(v) for v in self.mesh.get().replace(",", " ").split()),
                    points_per_segment=int(self.points.get())))
            self.runner.root, self.runner.model = resolve_kssolv(project=self.project), model
            self.selected = self.runner.submit(request)
        except ValidationError as exc:
            fields = [" / ".join(str(v) for v in error["loc"]) for error in exc.errors()]
            messagebox.showerror("请检查输入", "以下输入不完整或超出允许范围：\n" + "\n".join(fields), parent=self.window)
            return
        except (ValueError, RuntimeError) as exc:
            messagebox.showerror("无法开始", str(exc), parent=self.window)
            return
        except OSError:
            messagebox.showerror("无法开始", "无法创建任务文件，请检查项目目录权限。", parent=self.window)
            return
        self._report_signature = None
        self.start_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        self.progress.start(12)
        self.refresh_history()
        self.jobs.selection_set(self.selected.name)

    def cancel(self):
        if self.runner.running and messagebox.askyesno("停止任务", "停止当前任务？已生成的文件会保留。", parent=self.window):
            self.cancel_button.configure(state="disabled")
            threading.Thread(target=self._cancel_safely, daemon=True).start()

    def _cancel_safely(self):
        try:
            self.runner.cancel()
        except Exception:
            self.cancel_error = "未能停止任务，请等待当前任务结束后关闭软件。"

    def refresh_history(self):
        selected = self.selected.name if self.selected else None
        self.jobs.delete(*self.jobs.get_children())
        for job in history(self.project):
            self.jobs.insert("", "end", iid=job["id"], values=(job["material"] if job["material"] != "—" else job["id"][:8], STATUS_LABELS.get(job["status"], job["status"])))
        if selected and self.jobs.exists(selected):
            self.jobs.selection_set(selected)

    def select_job(self, event=None):
        selected = self.jobs.selection()
        if selected:
            self.selected = self.project / "runs" / selected[0]
            self._report_signature = None
            self.plot_choice.set("")
            self.refresh_output()

    def refresh_output(self):
        if not self.selected:
            return
        state = read_json(self.selected / "status.json")
        if self.jobs.exists(self.selected.name):
            self.jobs.set(self.selected.name, "state", STATUS_LABELS.get(state.get("status"), state.get("status", "—")))
            material = read_json(self.selected / "selection.json").get("formula")
            if material:
                self.jobs.set(self.selected.name, "material", material)
        label = STATUS_LABELS.get(state.get("status"), state.get("status", "等待状态"))
        if self.runner.running and self.selected != self.runner.output:
            label += "（另有当前任务正在运行）"
        self.status.set(label + ("；" + state["error"] if state.get("error") else ""))
        report = self.selected / "report.md"
        signature = (self.selected, report.stat().st_mtime_ns if report.exists() else 0)
        if signature != self._report_signature:
            self.set_text(self.report, ("点击上方“打开图文报告”查看并保存含全部图片的报告。\n\n" + report.read_text(encoding="utf-8")) if report.exists() else "报告尚未生成。\n\n可切换到“日志”查看进度，或点击“打开结果目录”查看已生成的输入文件。")
            self._report_signature = signature
        entries = []
        events = self.selected / "events.jsonl"
        if events.exists():
            for line in events.read_text(encoding="utf-8").splitlines()[-150:]:
                try:
                    import json
                    item = json.loads(line)
                    entries.append(STATUS_LABELS.get(item["status"], item["status"]) + (" · " + item["error"] if item.get("error") else ""))
                except (ValueError, KeyError):
                    continue
        for name in ["engine_console.log", "matlab.log"]:
            file = self.selected / name
            if file.exists():
                with file.open("rb") as stream:
                    stream.seek(max(0, file.stat().st_size - 16000))
                    entries.append("\n--- " + name + " ---\n" + stream.read().decode("utf-8", errors="replace"))
        self.set_text(self.logs, "\n".join(entries) or "等待日志…")
        plots = sorted(p.name for p in self.selected.glob("band_*.png"))
        self.plot_list.configure(values=plots)
        if self.plot_choice.get() not in plots:
            self.plot_choice.set(plots[0] if plots else "")
            self.show_plot()

    def show_plot(self):
        if not self.selected or not self.plot_choice.get():
            self.image = None
            self.plot_label.configure(image="", text="当前任务尚无能带图。")
            return
        try:
            image = tk.PhotoImage(file=str(self.selected / self.plot_choice.get()))
            import math
            factor = max(1, math.ceil(image.width() / 670), math.ceil(image.height() / 310))
            self.image = image.subsample(factor, factor)
            self.plot_label.configure(image=self.image, text="")
        except tk.TclError:
            self.plot_label.configure(image="", text="图片正在写入或无法预览，请在结果目录查看。")

    def open_report(self):
        if not self.selected or not (self.selected / "report.md").exists():
            messagebox.showinfo("图文报告", "请先选择已经生成报告的任务。", parent=self.window)
            return
        try:
            from .reporting import export_html
            path = export_html(self.selected)
            if os.name == "nt":
                os.startfile(path)
            else:
                import webbrowser
                webbrowser.open(path.as_uri())
        except OSError:
            messagebox.showerror("图文报告", "无法生成或打开报告，请检查结果目录权限及默认浏览器设置。", parent=self.window)

    def open_output(self):
        path = self.selected or self.project / "runs"
        path.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(path)
        elif os.name == "posix":
            subprocess.Popen(["open" if __import__("sys").platform == "darwin" else "xdg-open", str(path)])

    def tick(self):
        if self.cancel_error:
            messagebox.showerror("停止任务", self.cancel_error, parent=self.window)
            self.cancel_error = None
            self._closing = False
        if self._closing and not self.runner.running:
            self.window.destroy()
            return
        active = self.runner.running
        self.start_button.configure(state="disabled" if active or self._closing else "normal")
        if not active:
            self.cancel_button.configure(state="disabled")
            self.progress.stop()
        self.refresh_output()
        if self.runner.last_error and self.selected == self.runner.output:
            self.status.set(self.runner.last_error)
        self.window.after(700, self.tick)

    def close(self):
        if self.runner.running:
            if not messagebox.askyesno("退出软件", "任务仍在运行。退出将停止当前任务，是否继续？", parent=self.window):
                return
            self._closing = True
            self.status.set("正在停止任务并退出…")
            threading.Thread(target=self._cancel_safely, daemon=True).start()
        else:
            self.window.destroy()


def main(project=None):
    if project is None:
        parser = argparse.ArgumentParser()
        parser.add_argument("--project", type=Path, default=Path.cwd())
        project = parser.parse_args().project
    try:
        window = tk.Tk()
        DesktopApp(window, project)
        window.mainloop()
    except Exception:
        import traceback
        runtime = Path(project) / ".runtime"
        runtime.mkdir(parents=True, exist_ok=True)
        (runtime / "desktop-error.log").write_text(traceback.format_exc(), encoding="utf-8")
        if os.name == "nt":
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, "桌面界面启动失败。请运行 install.cmd 检查环境，或查看 .runtime/desktop-error.log。", TITLE, 0x10)
        raise


if __name__ == "__main__":
    main()
