import base64
from kssolv_crew.reporting import export_html


def test_portable_report_embeds_actual_figures_and_escapes_untrusted_text(tmp_path):
    (tmp_path / "report.md").write_text('# 碳报告\n<script>alert(1)</script>\n![图](https://bad.example/x.png)', encoding="utf-8")
    png = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a9XkAAAAASUVORK5CYII=')
    (tmp_path / 'band_001_01.png').write_bytes(png)
    html = export_html(tmp_path).read_text(encoding='utf-8')
    assert '<h1>碳报告</h1>' in html
    assert '<script>' not in html and '&lt;script&gt;' in html
    assert 'https://bad.example' not in html
    assert f'data:image/png;base64,{base64.b64encode(png).decode()}' in html
    assert 'band_001_01.png' in html


def test_prepare_only_report(tmp_path):
    (tmp_path / 'report.md').write_text('仅生成输入', encoding='utf-8')
    assert '尚无能带图片' in export_html(tmp_path).read_text(encoding='utf-8')
