"""高考语文刷题助手 — CLI 入口

Usage:
    # 单次评估
    python -m src.main evaluate --image answer.jpg --type big_essay --question "请以'韧性'为题写一篇议论文"

    # 批量评估
    python -m src.main batch --dir ./photos/ --type modern_reading

    # 查看错题本
    python -m src.main mistakes --type big_essay --output mistake_book.html

    # 启动 Web UI
    python -m src.main ui

    # 查看统计
    python -m src.main stats

    # 初始化数据库
    python -m src.main init
"""

import argparse
import logging
import sys
from pathlib import Path

# 确保项目根目录在 sys.path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 加载 .env
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("gaokao-agent")


def cmd_init(args):
    """初始化数据库"""
    from src.storage.database import init_db
    db_path = init_db()
    print(f"✅ 数据库初始化完成: {db_path}")
    print(f"   表: submissions, knowledge_mastery, practice_stats")


def cmd_evaluate(args):
    """评估单张图片"""
    from src.evaluator.pipeline import EvaluationPipeline

    if not args.image and not args.text:
        print("❌ 请指定 --image <图片路径> 或 --text <学生作答文本>")
        return

    # 纯文本模式（跳过 OCR）
    if args.text:
        pipeline = EvaluationPipeline()
        result = pipeline.run_text_only(
            ocr_text=args.text,
            question_type=args.type,
            question_text=args.question or "",
            save_to_db=not args.no_save,
        )
    elif args.image:
        if not Path(args.image).exists():
            print(f"❌ 图片不存在: {args.image}")
            return

        pipeline = EvaluationPipeline()

        result = pipeline.run(
            image_path=args.image,
            question_type=args.type,
            question_text=args.question or "",
            save_to_db=not args.no_save,
        )

    print(f"\n{'='*60}")
    print(f"📊 评估结果")
    print(f"{'='*60}")
    print(f"OCR 置信度: {result['ocr_confidence']:.1%}")

    if result['ocr_warnings']:
        print(f"\n⚠️ OCR 警告:")
        for w in result['ocr_warnings']:
            print(f"  - {w}")

    print(f"\n✅ 优点:")
    for s in result['evaluation'].get('strengths', [])[:3]:
        print(f"  ✓ {s.get('point', '')}")

    print(f"\n⚠️ 需要改进:")
    for w in result['evaluation'].get('weaknesses', [])[:3]:
        sev = w.get('severity', 'medium')
        print(f"  [{sev}] {w.get('point', '')}")

    print(f"\n🏷️ 标签: {', '.join(result['evaluation'].get('mistake_tags', []))}")

    if result['report_path']:
        print(f"\n📄 报告: {result['report_path']}")

    if result['submission_id']:
        print(f"💾 数据库ID: {result['submission_id']}")

    # 输出综合评价
    overall = result['evaluation'].get('overall_assessment', '')
    if overall:
        print(f"\n🎯 综合评价:\n{overall}")


def cmd_batch(args):
    """批量评估"""
    from src.evaluator.pipeline import EvaluationPipeline
    from src.storage.database import init_db

    # 确保数据库初始化
    init_db()

    image_dir = Path(args.dir)
    if not image_dir.exists():
        print(f"❌ 目录不存在: {args.dir}")
        return

    # 查找图片
    extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.webp', '.tiff'}
    images = sorted([
        f for f in image_dir.iterdir()
        if f.suffix.lower() in extensions
    ])

    if not images:
        print(f"❌ 未找到图片文件")
        return

    print(f"找到 {len(images)} 张图片\n")

    pipeline = EvaluationPipeline()
    results = []

    for i, img_path in enumerate(images, 1):
        print(f"\n[{i}/{len(images)}] {img_path.name}")

        try:
            result = pipeline.run(
                image_path=img_path,
                question_type=args.type,
                question_text=args.question or "",
                save_to_db=not args.no_save,
            )
            results.append(result)
            print(f"  OCR 置信度: {result['ocr_confidence']:.1%}")
        except Exception as e:
            logger.error(f"评估失败: {img_path.name} - {e}")
            continue

    # 汇总
    print(f"\n{'='*60}")
    print(f"批量评估完成: {len(results)}/{len(images)} 成功")


def cmd_mistakes(args):
    """查看/导出错题本"""
    from src.storage.database import get_mistakes
    from src.rendering.markdown_render import render_mistake_book
    from src.storage.database import init_db

    init_db()

    records = get_mistakes(
        question_type=args.type or None,
        limit=args.limit or 100,
    )

    if not records:
        print("✅ 暂无错题记录")
        return

    md_content = render_mistake_book(records, title="北京卷语文错题本")

    # 输出
    output_path = args.output
    if output_path:
        output_path = Path(output_path)

        if output_path.suffix == '.html':
            # HTML 导出
            from src.rendering.html_render import render_html_mistake_book
            html = render_html_mistake_book(md_content, "北京卷语文错题本")
            output_path.write_text(html, encoding='utf-8')
        else:
            output_path.write_text(md_content, encoding='utf-8')

        print(f"📄 错题本已导出: {output_path}")
    else:
        print(f"\n共 {len(records)} 条错题记录\n")
        print(md_content[:3000])
        if len(md_content) > 3000:
            print(f"\n... (全文共 {len(md_content)} 字符，使用 --output 导出)")


def cmd_stats(args):
    """查看练习统计"""
    from src.storage.database import get_knowledge_stats, get_mistakes

    knowledge = get_knowledge_stats()
    mistakes = get_mistakes(limit=1000)

    print(f"\n{'='*60}")
    print(f"📊 练习统计")
    print(f"{'='*60}")

    print(f"\n总错题数: {len(mistakes)}")

    # 按题型分布
    type_count = {}
    for m in mistakes:
        type_count[m.question_type] = type_count.get(m.question_type, 0) + 1

    if type_count:
        print(f"\n错题分布:")
        type_names = {
            "big_essay": "大作文",
            "modern_reading": "现代文阅读",
            "classical_chinese": "文言文",
            "poetry": "诗歌鉴赏",
            "micro_essay": "微写作",
        }
        for t, c in sorted(type_count.items(), key=lambda x: x[1], reverse=True):
            name = type_names.get(t, t)
            bar = "█" * min(c, 30)
            print(f"  {name}: {bar} ×{c}")

    # 知识点弱点
    if knowledge:
        print(f"\n薄弱知识点 Top 5:")
        for k in knowledge[:5]:
            ratio = f"{k['mistake_count']}/{k['total_attempts']}"
            print(f"  - {k['knowledge_point']} ({k['question_type']}): {ratio}")


def cmd_ui(args):
    """启动 Web UI"""
    try:
        from src.ui.app import create_app
        app, css = create_app()
        app.launch(
            server_port=args.port or 7860,
            share=args.share or False,
            inbrowser=True,
            css=css,
        )
    except ImportError as e:
        print(f"❌ 无法启动 Web UI: {e}")
        print("   请安装: pip install gradio")


def main():
    parser = argparse.ArgumentParser(
        description="高考语文刷题助手 — 北京卷专用 AI 评估工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python -m src.main evaluate -i answer.jpg -t big_essay -q "请以'韧性'为题写议论文"
  python -m src.main batch -d ./photos/ -t modern_reading
  python -m src.main mistakes -t big_essay -o mistake_book.html
  python -m src.main stats
  python -m src.main ui
        """
    )
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # init
    p_init = subparsers.add_parser("init", help="初始化数据库")

    # evaluate
    p_eval = subparsers.add_parser("evaluate", help="评估单张学生作答图片")
    p_eval.add_argument("-i", "--image", help="学生作答图片路径")
    p_eval.add_argument("--text", help="跳过 OCR，直接提交文本评估")
    p_eval.add_argument("-t", "--type", required=True,
                        choices=["big_essay", "modern_reading", "classical_chinese",
                                 "poetry", "micro_essay"],
                        help="题型")
    p_eval.add_argument("-q", "--question", default="", help="题干文本")
    p_eval.add_argument("--no-save", action="store_true", help="不保存到数据库")

    # batch
    p_batch = subparsers.add_parser("batch", help="批量评估")
    p_batch.add_argument("-d", "--dir", required=True, help="图片目录")
    p_batch.add_argument("-t", "--type", required=True,
                         choices=["big_essay", "modern_reading", "classical_chinese",
                                  "poetry", "micro_essay"],
                         help="题型")
    p_batch.add_argument("-q", "--question", default="", help="题干文本")
    p_batch.add_argument("--no-save", action="store_true", help="不保存到数据库")

    # mistakes
    p_mis = subparsers.add_parser("mistakes", help="查看/导出错题本")
    p_mis.add_argument("-t", "--type", help="按题型筛选")
    p_mis.add_argument("-o", "--output", help="导出路径 (.md 或 .html)")
    p_mis.add_argument("--limit", type=int, default=100, help="最大条数")

    # stats
    p_stats = subparsers.add_parser("stats", help="查看练习统计")

    # ui
    p_ui = subparsers.add_parser("ui", help="启动 Web 界面")
    p_ui.add_argument("-p", "--port", type=int, default=7860, help="端口")
    p_ui.add_argument("--share", action="store_true", help="生成公网链接")

    # 解析
    args = parser.parse_args()

    if args.command == "init":
        cmd_init(args)
    elif args.command == "evaluate":
        cmd_evaluate(args)
    elif args.command == "batch":
        cmd_batch(args)
    elif args.command == "mistakes":
        cmd_mistakes(args)
    elif args.command == "stats":
        cmd_stats(args)
    elif args.command == "ui":
        cmd_ui(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
