# Quick Start · 5 分钟跑出第 1 集

## 0. 前置条件

- Python 3.10+
- ffmpeg(命令行 `ffmpeg -version` 可用)
- OpenAI API key

## 1. 装依赖

```bash
git clone https://github.com/Forlives/nce-video-pipeline
cd nce-video-pipeline
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env, 填 OPENAI_API_KEY
```

## 2. 至少放一张背景图

```bash
# 占位用,后期替换成自己的素材
curl https://picsum.photos/1280/720 -o assets/background.png
```

## 3. 跑第 1 集

```bash
python -m scripts.generate_all --range 1-1
```

输出在 `output/<project_id>/`:
- `script.json` — GPT 改编后的脚本(场景化)
- `audio/scene_001.mp3 ...` — 各段配音
- `subtitles.srt` — 双语字幕
- `final.mp4` — **最终视频**

## 4. 查看进度

```bash
# 启动 API 看进度
uvicorn src.main:app --port 8000
# 浏览器: http://localhost:8000/docs (Swagger)
```

## 5. 批量产出

```bash
# 跑前 10 课
python -m scripts.generate_all --range 1-10 --concurrency 2

# 全部 30 课(注意 OpenAI API 费用 ~$1-3)
python -m scripts.generate_all
```

## 6. 启用数字人(可选)

见 [INFINITETALK_DEPLOY.md](INFINITETALK_DEPLOY.md)。
