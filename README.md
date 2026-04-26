# NCE Video Pipeline · 新概念英语 AI 视频生产管线

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)]()

> **从一篇 NCE 课文 → 全自动产出一集双语短视频** · 支持 GPT-4o 改编、OpenAI TTS 配音、双语 SRT、ffmpeg 拼接、可选 InfiniteTalk 数字人

---

## ✨ 核心特性

- 🤖 **多模型 LLM 智能改编**:OpenAI / **Claude(via OpenRouter)** / DeepSeek / 任意 OneAPI 兼容中转,改 .env 即可切换
- 🎙️ **OpenAI TTS 真人级配音**:多种音色,英文旁白逐场景生成,支持独立 key/base_url(混搭省钱)
- 📝 **双语 SRT 字幕**:英文 + 中文 + 关键词高亮
- 🎬 **ffmpeg 自动拼接**:静态背景图 + 多段音频 + 字幕 + 可选 BGM
- 🤳 **可选数字人(GPU)**:接入远程 [InfiniteTalk](https://github.com/bmwas/InfiniteTalk) 服务,生成数字人讲师视频
- 🚀 **REST API + 批量脚本**:FastAPI 后端 + `python -m scripts.generate_all` 一行批量产出
- 📚 **30 课首发课文**:NCE 1 册前 30 课 JSON 已收录,开箱即用

---

## 📐 架构

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                  │
│  Lesson(JSON)                                                   │
│      ↓                                                           │
│  ScriptGenerator    (GPT-4o)         → AdaptedScript            │
│      ↓                                                           │
│  TTSService         (OpenAI TTS)     → audio/scene_*.mp3        │
│      ↓                                                           │
│  SubtitleService    (in-process)     → subtitles.srt            │
│      ↓                                                           │
│  ★ DigitalHumanService(可选, 远程 GPU 跑 InfiniteTalk)            │
│      ↓                                                           │
│  VideoAssembler     (ffmpeg 真调用)  → final.mp4                │
│      ↓                                                           │
│  Publisher          (douyin/bilibili/xhs/youtube/tiktok)        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

> **重点**:除了"数字人(★)"这一步需要 GPU 服务器,其余全部 CPU + OpenAI API 即可,你的笔记本/普通云服务器就能跑。

---

## 🚀 快速开始

### 1. 克隆 + 安装依赖

```bash
git clone https://github.com/Forlives/nce-video-pipeline
cd nce-video-pipeline
pip install -r requirements.txt
```

### 2. 准备 `.env`(三选一)

```bash
cp .env.example .env
```

**A. OpenAI 官方 GPT-4o**(默认):
```env
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o
```

**B. Claude 3.5 Sonnet(via OpenRouter,一个 key 玩遍主流模型)**:
```env
OPENAI_API_KEY=sk-or-v1-xxx
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENAI_MODEL=anthropic/claude-3.5-sonnet
TTS_API_KEY=sk-openai-xxx          # TTS 独立 key (OpenRouter 不做 TTS)
TTS_BASE_URL=https://api.openai.com/v1
```

**C. DeepSeek(国内便宜)**:
```env
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://api.deepseek.com/v1
OPENAI_MODEL=deepseek-chat
TTS_API_KEY=sk-openai-xxx
TTS_BASE_URL=https://api.openai.com/v1
```

> **TTS 必须用 OpenAI 兼容 / 官方 key**(中转大多不支持 audio),所以建议 LLM 和 TTS 用两套 key 混搭。

### 3. 准备 ffmpeg

确保命令行 `ffmpeg -version` 能输出版本信息(Windows 用户可在 [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) 下载并加入 PATH)。

### 4. (可选)准备素材

```bash
# 至少放一张背景图(否则视频只有黑屏 + 音频 + 字幕)
curl https://picsum.photos/1280/720 -o assets/background.png
```

### 5. 跑第一集

```bash
# 方式 A: 启动 FastAPI, 用 /api/v1/generate 触发
uvicorn src.main:app --reload --port 8000

# 方式 B: 命令行批量
python -m scripts.generate_all --range 1-1
```

完成后:`output/<project_id>/final.mp4`

---

## 📁 目录结构

```
nce-video-pipeline/
├── README.md
├── requirements.txt
├── pyproject.toml
├── .env.example
├── .gitignore
├── config/
│   ├── settings.py         # Pydantic Settings (env-driven)
│   └── __init__.py
├── src/
│   ├── main.py             # FastAPI 入口 + Pipeline 装配
│   ├── api/routes.py       # REST API: /api/v1/{generate,projects/...}
│   ├── pipeline/pipeline.py
│   ├── models/             # Pydantic: Lesson / AdaptedScript / VideoProject
│   └── services/
│       ├── openai_llm.py
│       ├── openai_tts.py
│       ├── tts_service.py
│       ├── subtitle_service.py
│       ├── script_generator.py
│       ├── video_assembler.py     # ★ 已升级为真调 ffmpeg
│       ├── digital_human_service.py  # ★ 新增 InfiniteTalk HTTP 客户端
│       └── publisher.py
├── data/
│   ├── lessons/            # ★ 30 课首发课文 JSON
│   └── sample_lessons/     # 旧示例(保留兼容性)
├── assets/                 # 背景图/BGM/avatar(自备, 见 assets/README.md)
├── scripts/
│   └── generate_all.py     # ★ 批量生成
├── docs/
│   ├── QUICKSTART.md
│   └── INFINITETALK_DEPLOY.md  # ★ GPU 服务器部署 InfiniteTalk
├── tests/                  # 14 个单元测试 (pytest)
└── output/                 # 生成的视频(运行时, 已 gitignore)
```

---

## 🧪 测试

```bash
pytest -v
pytest --cov=src --cov-report=term-missing
```

要求覆盖率 ≥ 80%(`pyproject.toml` 已配置 `fail_under=80`)。

---

## 🌐 API

启动:`uvicorn src.main:app --reload --port 8000`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/health` | 健康检查 |
| POST | `/api/v1/generate` | 启动新视频任务(异步) |
| GET | `/api/v1/projects` | 列出所有任务 |
| GET | `/api/v1/projects/{id}` | 单任务详情 |
| DELETE | `/api/v1/projects/{id}` | 删除任务 |
| POST | `/api/v1/projects/{id}/cancel` | 取消运行中任务 |

**示例**:

```bash
curl -X POST http://localhost:8000/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{
    "lesson_id": 1,
    "title": "Excuse me!",
    "text": "Excuse me! Yes? Is this your handbag? Yes, it is.",
    "level": "beginner",
    "vocabulary": ["excuse", "handbag"],
    "style": "modern_dialogue",
    "platforms": []
  }'
```

---

## 🤳 启用数字人(InfiniteTalk @ GPU)

**默认不启用** — 视频用静态背景图。

要让讲师变成 AI 数字人:
1. 在你的 GPU 服务器(8GB+ 显存)上按 [docs/INFINITETALK_DEPLOY.md](docs/INFINITETALK_DEPLOY.md) 部署 HTTP 服务
2. 在 `.env` 设置 `INFINITETALK_API_URL=http://你的GPU服务器:8000`
3. 准备一张 `assets/avatar.png` 作为数字人参考图
4. 重启 pipeline,会自动调用

不需要修改任何代码,即插即用。

---

## 📅 自媒体起号建议

NCE 1-4 册共 **432 课**,够你日更 1-2 年:

| 平台 | 单集时长 | 频率建议 | 风格 |
|------|---------|---------|------|
| 抖音 / 视频号 | 30-60s | 每天 1-2 集 | sitcom(情景剧) |
| B 站 / 油管 | 3-10 分钟 | 每周 3-5 集 | story(完整故事改编) |
| 小红书 | 静态图 + 字幕 + 短解释 | 每天 1 篇 | modern_dialogue |
| TikTok | 15-30s | 每天 1-3 集 | sitcom |

⚠️ **AI 标识**:抖音/视频号要求 AI 生成内容必须打标识,详见各平台《算法解释规则》。

---

## 🤝 贡献

- 补充课文:把 NCE 第 31-432 课写进 `data/lessons/lesson_NN.json` 提 PR
- 改进 prompt:`src/services/script_generator.py` 里的 `SYSTEM_PROMPT`
- 新增 Publisher 适配器:抖音/B 站/油管的真上传逻辑

---

## 📜 License

MIT. 注意 NCE 教材本身有版权,**生成内容仅供学习交流,商用前请确认教材版权情况**。
