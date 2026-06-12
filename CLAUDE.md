# 高考语文刷题助手 — Project Context

## What This Is
面向北京卷高考语文的 AI 刷题助手，运行于 Windows PC。输入学生手写答案图片，输出北京卷评分标准的优缺点分析和改进建议。

## Architecture
```
图片 → PaddleOCR(本地手写识别) → DeepSeek API(评估) → Markdown/HTML报告
                                ↑ 可选: 豆包 Vision Pro 兜底
```

## Key Commands
```bash
python -m src.main init                          # 初始化数据库
python -m src.main evaluate -i <img> -t <type>   # 评估单张图片
python -m src.main batch -d <dir> -t <type>      # 批量评估
python -m src.main mistakes -o <path>            # 导出错题本
python -m src.main stats                         # 查看统计
python -m src.main ui                            # 启动 Web UI
```

## 题型代码
`big_essay`(大作文) `modern_reading`(现代文阅读) `classical_chinese`(文言文) `poetry`(诗歌) `micro_essay`(微写作)

## Key Modules
- `src/ocr/` — PaddleOCR 手写识别 (preprocessor → recognizer → postprocessor)
- `src/llm/` — LLM 统一客户端 (OpenAI 兼容协议, 支持 DeepSeek/豆包/千问/GLM 切换)
- `src/evaluator/` — 评估管线 (pipeline 编排, grader 评分)
- `src/storage/` — SQLite 持久化 (database CRUD, models)
- `src/rendering/` — Markdown/HTML 报告渲染
- `src/ui/` — Gradio Web 界面
- `src/kb/` — RAG 知识库 (Phase 2)
- `config/` — LLM 配置 (llm.yaml) + 北京卷评分标准 (beijing_gaokao.yaml)
