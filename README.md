# 高考语文刷题助手 — 北京卷专用

> AI 判题 · 手写识别 · 错题管理 · 一键导出 PDF

面向北京卷高考语文开放性题型（阅读、作文、微写作等），上传学生手写答案图片，自动 OCR 识别 + DeepSeek V4 Pro 评估，输出优缺点分析和改进建议，支持 PDF/Markdown 报告导出。

## 快速开始

### 1. 下载

从 [Releases](https://github.com/Sean-Halford/gaokaoagent/releases) 下载最新版 `GaokaoAgent-v1.0.zip`，解压到任意目录。

> 如果没有 Release，可从源码运行（见下方[从源码运行](#从源码运行)），或自行打包：
> ```bash
> cd gaokaoagent
> build.ps1
> # 产物在 dist/GaokaoAgent/，压缩后约 399 MB
> ```

### 2. 启动

双击 `start.bat`，浏览器自动打开 `http://127.0.0.1:7860/`。

### 3. 配置 API Key

在 Web 界面左侧「🔑 API 配置」区域：

| 设置 | 说明 |
|------|------|
| 模型厂商 | 选择 DeepSeek（默认） |
| API Key | 粘贴你的 Key，留空则读取 `.env` 文件 |

然后上传手写答案图片，选择题型，点击「开始评估」。

## 架构

```
手写图片 → PaddleOCR (本地识别) → DeepSeek V4 Pro (评估) → PDF/Markdown 报告
```

- **OCR**：PaddleOCR v2.8，本地运行，支持手写中文
- **LLM**：Anthropic 兼容协议调用 DeepSeek，支持豆包/千问/智谱切换

## 支持题型

| 题型 | 代码 |
|------|------|
| 📝 大作文 | `big_essay` |
| 📖 现代文阅读 | `modern_reading` |
| 📜 文言文阅读 | `classical_chinese` |
| 🎋 古代诗歌阅读 | `poetry` |
| ✏️ 微写作 | `micro_essay` |

## 从源码运行

### 环境要求

- Python 3.11（PaddleOCR 兼容）
- Windows 10/11

### 安装

```bash
# 克隆仓库
git clone https://github.com/Sean-Halford/gaokaoagent.git
cd gaokaoagent

# 创建虚拟环境
python -m venv venv
venv\Scripts\activate

# 安装依赖
pip install paddlepaddle==2.6.2 -i https://www.paddlepaddle.org.cn/packages/stable/cpu/
pip install paddleocr==2.8.1
pip install anthropic openai gradio pyyaml python-dotenv pydantic Pillow weasyprint markdown jinja2

# 配置 API Key
copy .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY=sk-xxx
```

### 首次运行 PaddleOCR

首次运行时 PaddleOCR 会自动下载模型（约 100 MB），存放于 `~/.paddleocr/`。

或者手动安装模型到 `C:\paddleocr_models\`：
```bash
python -c "from paddleocr import PaddleOCR; PaddleOCR(lang='ch')"
```

### 启动

```bash
python -m src.main ui          # Web 界面
python -m src.main evaluate -i answer.jpg -t big_essay   # CLI 评估
python -m src.main mistakes -o mistake_book.html         # 导出错题本
python -m src.main stats                                  # 统计
```

## 项目结构

```
├── src/
│   ├── ocr/           # PaddleOCR 手写识别
│   ├── llm/           # LLM 客户端（Anthropic/OpenAI 协议）
│   ├── evaluator/     # 评估管线（OCR → LLM → 报告）
│   ├── storage/       # SQLite 持久化
│   ├── rendering/     # Markdown/PDF 报告渲染
│   └── ui/            # Gradio Web 界面
├── config/
│   ├── llm.yaml                      # LLM 提供商配置
│   └── beijing_gaokao.yaml           # 北京卷评分标准
├── data/raw/                         # 真题 PDF 存放（RAG Phase 2）
├── output/                           # 报告输出
└── templates/                        # HTML/Markdown 模板
```

## API Key 获取

| 厂商 | 地址 | 新用户额度 |
|------|------|-----------|
| DeepSeek | [platform.deepseek.com](https://platform.deepseek.com/api_keys) | 500 万 token |
| 豆包 | [console.volcengine.com/ark](https://console.volcengine.com/ark) | 50 万 token |
| 千问 | [dashscope.console.aliyun.com](https://dashscope.console.aliyun.com/apiKey) | 100 万 token |
| 智谱 | [open.bigmodel.cn](https://open.bigmodel.cn/usercenter/apikeys) | 200 万 token |

## 发布 Release

打包后的 ZIP 约 399 MB（含 Python + PaddleOCR 模型），需要手动上传到 GitHub Release。

### 1. 本地打包

```powershell
cd gaokaoagent
.\build.ps1
# 产物: dist/GaokaoAgent-v1.0.zip (~399 MB)
```

### 2. 创建 Release

1. 打开 [Releases 页面](https://github.com/Sean-Halford/gaokaoagent/releases)
2. 点击 **Draft a new release**
3. Tag: `v1.0`（create new tag）
4. Title: `GaokaoAgent v1.0`
5. 上传 `dist/GaokaoAgent-v1.0.zip`
6. 点击 **Publish release**

> GitHub Release 单个文件最大 2 GB，399 MB 直接上传即可，无需 Git LFS。

## License

MIT
