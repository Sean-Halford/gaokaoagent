"""HTML/PDF 报告渲染"""

import markdown
from datetime import datetime
from pathlib import Path


def md_to_html(md_content: str, title: str = "评估报告") -> str:
    """将 Markdown 转为完整 HTML 页面"""
    md = markdown.Markdown(extensions=[
        'markdown.extensions.tables',
        'markdown.extensions.fenced_code',
        'markdown.extensions.codehilite',
        'markdown.extensions.toc',
    ])
    body = md.convert(md_content)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} — 高考语文刷题助手</title>
    <style>
        :root {{ --primary: #1e40af; --text: #1f2937; --border: #e5e7eb;
                --code-bg: #f3f4f6; --highlight: #dbeafe; }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: "PingFang SC", "Microsoft YaHei", "SimSun", serif;
            color: var(--text); background: white;
            line-height: 1.8; max-width: 900px; margin: 0 auto; padding: 2em;
        }}
        h1 {{ font-size: 1.8em; color: var(--primary);
              border-bottom: 3px solid var(--primary); padding-bottom: .3em; }}
        h2 {{ font-size: 1.3em; color: var(--primary); margin-top: 1.5em;
              border-bottom: 1px solid var(--border); padding-bottom: .2em; }}
        h3 {{ font-size: 1.1em; margin-top: 1.2em; }}
        blockquote {{ border-left: 4px solid var(--primary); padding: .4em 1em;
                     background: var(--highlight); border-radius: 0 4px 4px 0; }}
        code {{ background: var(--code-bg); padding: .15em .4em; border-radius: 3px; }}
        table {{ width: 100%; border-collapse: collapse; margin: .8em 0; }}
        th, td {{ border: 1px solid var(--border); padding: .5em; text-align: left; }}
        th {{ background: #f9fafb; font-weight: 600; }}
        hr {{ border: none; border-top: 1px solid var(--border); margin: 1.5em 0; }}
        details {{ margin: .5em 0; padding: .3em .8em; border: 1px solid var(--border); border-radius: 4px; }}
        summary {{ cursor: pointer; font-weight: 600; color: var(--primary); }}
        @media print {{
            body {{ font-size: 12pt; max-width: none; padding: 0; }}
            @page {{ margin: 2cm; size: A4; }}
        }}
    </style>
</head>
<body>
{body}
</body>
</html>"""


def md_to_pdf(md_content: str, output_path: str | Path,
              title: str = "评估报告") -> Path | None:
    """将 Markdown 转为 PDF 文件

    Args:
        md_content: Markdown 文本
        output_path: PDF 输出路径
        title: 文档标题

    Returns:
        PDF 文件路径，失败返回 None
    """
    html = md_to_html(md_content, title)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        import os
        # Work around fontconfig issue with Chinese usernames on Windows
        os.environ.setdefault('FONTCONFIG_PATH', 'C:\\Windows\\Fonts')
        os.environ.setdefault('FONTCONFIG_FILE', '')
        from weasyprint import HTML
        HTML(string=html).write_pdf(str(output_path))
        return output_path
    except ImportError:
        html_path = output_path.with_suffix('.html')
        html_path.write_text(html, encoding='utf-8')
        return html_path
    except Exception as e:
        logger = __import__('logging').getLogger(__name__)
        logger.warning(f"PDF 生成失败，回退到 HTML: {e}")
        html_path = output_path.with_suffix('.html')
        html_path.write_text(html, encoding='utf-8')
        return html_path
