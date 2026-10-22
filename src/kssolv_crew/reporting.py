"""Portable local report with embedded figures; no external resources or scripts."""
import base64
from html import escape
from pathlib import Path
import re


def export_html(output):
    output = Path(output)
    text = (output / "report.md").read_text(encoding="utf-8")
    # Figures are collected from the job directory, never from LLM-provided URLs.
    text = re.sub(r"!\[[^\]]*\]\([^\n]*\)", "", text)
    paragraphs = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        heading = re.match(r"^(#{1,3})\s+(.+)$", line)
        if heading:
            level = len(heading[1])
            paragraphs.append(f"<h{level}>{escape(heading[2])}</h{level}>")
        else:
            paragraphs.append(f"<p>{escape(line)}</p>")
    figures = []
    for image in sorted(output.glob("band_*.png")):
        if image.is_symlink() or not image.is_file():
            continue
        data = base64.b64encode(image.read_bytes()).decode("ascii")
        figures.append(f'<figure><img src="data:image/png;base64,{data}" alt="{escape(image.name)}">'
                       f'<figcaption>{escape(image.name)}</figcaption></figure>')
    document = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src data:; style-src 'unsafe-inline'">
<title>KSSOLV 能带计算报告</title><style>
body{font:16px/1.7 "Microsoft YaHei",sans-serif;color:#172334;background:#f3f5f8;margin:0}
main{max-width:960px;margin:24px auto;padding:32px;background:white}
h1,h2,h3{line-height:1.4}p{overflow-wrap:anywhere}figure{margin:24px 0;break-inside:avoid}
img{display:block;max-width:100%;height:auto;margin:auto}figcaption{text-align:center;color:#536277}
.note{padding:12px;background:#edf3fa} @media print{body{background:white}main{margin:0;padding:0}}
</style><main><p class="note">此文件已内嵌能带图片，可单独复制分享。可用浏览器打印功能保存为 PDF。
计算完成不代表已完成物理参数的系统收敛验证。</p>'''
    document += "\n".join(paragraphs)
    document += '<h2>能带图片</h2>' + ("\n".join(figures) or '<p>本任务尚无能带图片。</p>')
    document += '</main></html>'
    target = output / "report.html"
    target.write_text(document, encoding="utf-8")
    return target
