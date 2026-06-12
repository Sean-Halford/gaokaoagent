"""高考语文刷题助手 — Gradio Web 界面"""

import os
import logging
from pathlib import Path
from datetime import datetime
import gradio as gr

logger = logging.getLogger(__name__)

QUESTION_TYPES = [
    ("📝 大作文", "big_essay"),
    ("📖 现代文阅读", "modern_reading"),
    ("📜 文言文阅读", "classical_chinese"),
    ("🎋 古代诗歌阅读", "poetry"),
    ("✏️ 微写作", "micro_essay"),
]

TYPE_LABELS: dict[str, str] = {
    "big_essay": "大作文",
    "modern_reading": "现代文阅读",
    "classical_chinese": "文言文阅读",
    "poetry": "古代诗歌阅读",
    "micro_essay": "微写作",
}

PROVIDER_CHOICES = [
    ("🤖 DeepSeek", "deepseek"),
    ("🫘 豆包 (火山引擎)", "doubao"),
    ("☁️ 千问 (阿里云)", "qwen"),
    ("🧠 智谱 GLM", "glm"),
]

PROVIDER_BASE_URLS: dict[str, str] = {
    "deepseek": "https://api.deepseek.com/anthropic",
    "doubao": "https://ark.cn-beijing.volces.com/api/v3",
    "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "glm": "https://open.bigmodel.cn/api/paas/v4",
}

CSS = """
body { font-family: "PingFang SC", "Microsoft YaHei", sans-serif; }
.header { text-align: center; padding: 1em 0 0.2em;
          background: #e8edf5; border-radius: 12px; color: #1e3a5f;
          margin-bottom: 1em; }
.header h1 { font-size: 1.7em; margin: 0; font-weight: 700; }
.header p { opacity: 0.7; margin: 0.2em 0 0; }
.result-section { background: #fafafa; border-radius: 10px; padding: 1em;
                  margin: 0.5em 0; border: 1px solid #e5e7eb; }
.tag { display: inline-block; padding: 0.15em 0.6em; border-radius: 999px;
       font-size: 0.82em; font-weight: 600; margin: 0.1em; }
.tag-critical { background: #fee2e2; color: #991b1b; }
.tag-high { background: #ffedd5; color: #9a3412; }
.tag-medium { background: #fef3c7; color: #92400e; }
.tag-low { background: #f0fdf4; color: #166534; }
.tag-info { background: #dbeafe; color: #1e40af; }
"""


def create_app():
    def run_evaluation(image, question_type, question_text, api_key, provider):
        from src.evaluator.pipeline import EvaluationPipeline

        if image is None:
            empty = "<div style='color:#999;text-align:center;padding:2em'>📷 请上传学生手写答案图片</div>"
            return (empty, "", "", None)

        base_url = PROVIDER_BASE_URLS.get(provider, "https://api.deepseek.com")
        # 厂商对应的默认模型
        default_models = {
            "deepseek": "deepseek-v4-pro[1m]",
            "doubao": "doubao-1.5-pro-32k",
            "qwen": "qwen-max",
            "glm": "glm-4-plus",
        }
        model_name = default_models.get(provider, "deepseek-v4-pro[1m]")

        try:
            pipeline = EvaluationPipeline()
            result = pipeline.run(
                image_path=image,
                question_type=question_type,
                question_text=question_text or "",
                save_to_db=True,
                api_key=api_key.strip() if api_key else "",
                base_url=base_url,
                model_name=model_name,
            )
        except Exception as e:
            logger.exception("评估失败")
            error_html = f"""
            <div style='background:#fef2f2;border:2px solid #fca5a5;border-radius:12px;
                        padding:2em;text-align:center;margin:1em 0;'>
              <h3 style='color:#dc2626;'>❌ 评估失败</h3>
              <p style='color:#7f1d1d;'>{e}</p>
              <p style='color:#9ca3af;font-size:0.85em;'>请检查图片是否清晰、API Key 是否正确、模型是否匹配</p>
            </div>"""
            return (error_html, "<div style='color:#999;padding:2em;'>评估失败</div>", "", None)

        eval_data = result["evaluation"]
        type_name = TYPE_LABELS.get(question_type, question_type)
        ocr_conf = result.get("ocr_confidence", 0)
        report_md = result.get("report_md", "")

        # ---- 生成 PDF (临时目录 + 同步保存到 output) ----
        pdf_path = None
        if report_md:
            from src.rendering.html_render import md_to_pdf
            import tempfile as _tmp
            from src.utils import get_output_dir
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")

            # 1. 生成到临时目录 (Gradio 安全路径要求)
            tmp_dir = Path(_tmp.gettempdir()) / "GaokaoAgent"
            tmp_dir.mkdir(parents=True, exist_ok=True)
            tmp_file = tmp_dir / f"{type_name}_{ts}.pdf"
            result_file = md_to_pdf(report_md, tmp_file, title=f"{type_name}评估报告")

            # 2. 同步保存一份到 output/exports 供长期留存
            try:
                keep_dir = get_output_dir() / "exports"
                keep_dir.mkdir(parents=True, exist_ok=True)
                md_to_pdf(report_md, keep_dir / f"{type_name}_{ts}.pdf",
                          title=f"{type_name}评估报告")
            except Exception:
                pass

            pdf_path = str(result_file) if result_file else None

        # ---- 主结果 HTML ----
        ocr_color = "#059669" if ocr_conf >= 0.8 else "#d97706" if ocr_conf >= 0.6 else "#dc2626"
        model_label = model_name

        parts = f"""
        <div style='text-align:center;padding:1em;background:#f0f9ff;border-radius:12px;margin-bottom:1em;'>
          <div style='font-size:1.2em;font-weight:700;color:#1e40af;'>{type_name} · 评估报告</div>
          <div style='margin-top:0.5em;font-size:0.88em;color:#6b7280;'>
            🔍 OCR: <span style='color:{ocr_color};font-weight:600;'>{ocr_conf:.0%}</span>
            &nbsp;|&nbsp; 🤖 {model_label}
            &nbsp;|&nbsp; 💾 ID:{result.get('submission_id', '-')}
          </div>
        </div>"""

        # 优点
        strengths = eval_data.get("strengths", [])
        parts += "<div class='result-section'><h3>✅ 优点</h3>"
        if strengths:
            parts += "<ul style='padding-left:1.2em;'>"
            for s in strengths:
                p = s.get("point", "") if isinstance(s, dict) else getattr(s, "point", "")
                d = s.get("detail", "") if isinstance(s, dict) else getattr(s, "detail", "")
                parts += f"<li><strong>{p}</strong>"
                if d:
                    parts += f"<br><span style='color:#6b7280;font-size:0.9em;'>{d}</span>"
                parts += "</li>"
            parts += "</ul>"
        else:
            parts += "<p style='color:#9ca3af;'>无</p>"
        parts += "</div>"

        # 缺点
        weaknesses = eval_data.get("weaknesses", [])
        sev_map = {"critical": ("tag-critical", "🔴"), "high": ("tag-high", "🟠"),
                   "medium": ("tag-medium", "🟡"), "low": ("tag-low", "🟢")}
        parts += "<div class='result-section'><h3>⚠️ 需要改进</h3>"
        if weaknesses:
            for w in weaknesses:
                p = w.get("point", "") if isinstance(w, dict) else getattr(w, "point", "")
                sev = w.get("severity", "medium") if isinstance(w, dict) else getattr(w, "severity", "medium")
                d = w.get("detail", "") if isinstance(w, dict) else getattr(w, "detail", "")
                sc, sl = sev_map.get(sev, ("tag-info", sev))
                parts += f"<p><span class='tag {sc}'>{sl} {sev}</span> <strong>{p}</strong></p>"
                if d:
                    parts += f"<p style='color:#6b7280;font-size:0.92em;padding-left:1em;'>{d}</p>"
                parts += "<br>"
        else:
            parts += "<p style='color:#9ca3af;'>暂无</p>"
        parts += "</div>"

        # 改进建议
        suggestions = eval_data.get("suggestions", [])
        parts += "<div class='result-section'><h3>💡 改进建议</h3>"
        if suggestions:
            for i, sug in enumerate(suggestions, 1):
                t = sug.get("target", "") if isinstance(sug, dict) else getattr(sug, "target", "")
                a = sug.get("action", "") if isinstance(sug, dict) else getattr(sug, "action", "")
                x = sug.get("practice", "") if isinstance(sug, dict) else getattr(sug, "practice", "")
                parts += f"<p><strong>{i}. {t}</strong></p>"
                parts += f"<p style='padding-left:1em;'>📋 {a}</p>"
                if x:
                    parts += f"<p style='padding-left:1em;color:#6b7280;font-size:0.9em;'>✏️ {x}</p>"
                parts += "<br>"
        else:
            parts += "<p style='color:#9ca3af;'>暂无</p>"
        parts += "</div>"

        # 标签
        tags = eval_data.get("mistake_tags", [])
        gaps = eval_data.get("knowledge_gaps", [])
        overall = eval_data.get("overall_assessment", "")
        parts += "<div class='result-section'><h3>🏷️ 错题标签</h3>"
        if tags:
            parts += "<p>" + " ".join([f"<span class='tag tag-high'>{t}</span>" for t in tags]) + "</p>"
        if gaps:
            parts += "<p style='margin-top:0.5em;'><strong>知识盲区:</strong> " + \
                " · ".join([f"<span class='tag tag-info'>{g}</span>" for g in gaps]) + "</p>"
        if not tags and not gaps:
            parts += "<p style='color:#9ca3af;'>无</p>"
        parts += "</div>"

        parts += "<div class='result-section'><h3>🎯 综合评价</h3>"
        parts += f"<p style='line-height:1.8;'>{overall or '无'}</p></div>"

        # OCR 文本
        ocr_text = result.get("ocr_text", "")
        warnings = result.get("ocr_warnings", [])
        ocr_html = "<div class='result-section'><h3>📝 OCR 识别文本</h3>"
        for w in warnings:
            ocr_html += f"<p style='color:#d97706;font-size:0.85em;'>⚠️ {w}</p>"
        if ocr_text:
            ocr_html += f"<pre style='white-space:pre-wrap;font-family:inherit;line-height:1.8;"
            ocr_html += f"background:#f8fafc;padding:1em;border-radius:8px;max-height:300px;"
            ocr_html += f"overflow-y:auto;'>{ocr_text}</pre>"
        else:
            ocr_html += "<p style='color:#9ca3af;'>未识别到文字</p>"
        ocr_html += "</div>"

        return (parts, ocr_html, report_md, pdf_path)

    with gr.Blocks(title="高考语文刷题助手") as app:
        gr.HTML("""
        <div class="header">
          <h1>📚 高考语文刷题助手</h1>
          <p>北京卷专用 · AI 判题 · 手写识别</p>
        </div>""")

        with gr.Row(equal_height=False):
            # === 左侧 ===
            with gr.Column(scale=1, min_width=300):
                gr.Markdown("### 📷 上传作答")

                image_input = gr.Image(label="学生手写答案图片", type="filepath", height=240)

                question_type = gr.Dropdown(
                    label="📋 题型", choices=QUESTION_TYPES, value="big_essay")

                question_text = gr.Textbox(
                    label="📖 题目原文（可选）",
                    placeholder="粘贴题干...", lines=3)

                with gr.Accordion("🔑 API 配置", open=True):
                    provider = gr.Dropdown(
                        label="🤖 模型厂商",
                        choices=PROVIDER_CHOICES,
                        value="deepseek",
                    )
                    api_key = gr.Textbox(
                        label="🔐 API Key",
                        placeholder="粘贴 Key",
                        type="password",
                    )

                with gr.Row():
                    submit_btn = gr.Button("🚀 开始评估", variant="primary", size="lg")
                    download_btn = gr.DownloadButton("📥 下载 PDF 报告", variant="secondary", size="lg")

            # === 右侧 ===
            with gr.Column(scale=2, min_width=500):
                with gr.Tabs():
                    with gr.TabItem("📊 评估结果"):
                        result_main = gr.HTML(
                            "<div style='text-align:center;color:#9ca3af;padding:3em 0;'>"
                            "<div style='font-size:3em;'>📤</div>"
                            "<p>上传图片并点击「开始评估」</p></div>")

                    with gr.TabItem("📝 OCR 识别"):
                        result_ocr = gr.HTML(
                            "<div style='color:#9ca3af;text-align:center;padding:2em;'>"
                            "提交后显示</div>")

                    with gr.TabItem("📄 Markdown"):
                        result_md = gr.Code(label="Markdown 原文", language="markdown",
                                            lines=20, interactive=False)

        submit_btn.click(
            fn=run_evaluation,
            inputs=[image_input, question_type, question_text, api_key, provider],
            outputs=[result_main, result_ocr, result_md, download_btn],
        )

    return app, CSS
