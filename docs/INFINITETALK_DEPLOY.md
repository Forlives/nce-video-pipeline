# InfiniteTalk 数字人 HTTP 服务部署指南

本项目通过 HTTP API 调用 InfiniteTalk(部署在 GPU 服务器上)。本文教你如何在你的 **3090 Ti / 4090 / 任意 8GB+ 显存 GPU 服务器** 上把 InfiniteTalk 包装成可调用的 HTTP 服务。

---

## 1. 在 GPU 服务器上安装 InfiniteTalk

参考 [github.com/bmwas/InfiniteTalk](https://github.com/bmwas/InfiniteTalk) 官方安装,或用以下一键脚本(Windows + RTX 3090 Ti):

<details>
<summary>展开:Windows PowerShell 一键脚本</summary>

```powershell
$ErrorActionPreference = 'Stop'
$BASE = 'D:\ai'
$PROJECT = "$BASE\InfiniteTalk"
$ENV_NAME = 'infinitetalk'

if (-not (Get-Command conda -ErrorAction SilentlyContinue)) {
    Invoke-WebRequest 'https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe' -OutFile "$env:TEMP\miniconda.exe"
    Start-Process "$env:TEMP\miniconda.exe" -ArgumentList '/S /InstallationType=JustMe /AddToPath=1 /D=C:\Miniconda3' -Wait
    $env:Path = "C:\Miniconda3;C:\Miniconda3\Scripts;$env:Path"
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) { winget install --id Git.Git -e --silent }

conda create -n $ENV_NAME python=3.10 -y
conda activate $ENV_NAME

$env:HF_ENDPOINT = 'https://hf-mirror.com'
$env:PIP_INDEX_URL = 'https://mirrors.aliyun.com/pypi/simple/'

pip install torch==2.4.1+cu121 torchvision==0.19.1+cu121 torchaudio==2.4.1+cu121 --index-url https://download.pytorch.org/whl/cu121
pip install xformers==0.0.28.post1 --index-url https://download.pytorch.org/whl/cu121
pip install opencv-python imageio einops huggingface_hub safetensors transformers accelerate diffusers librosa soundfile scipy fastapi uvicorn python-multipart
pip install https://github.com/bdashore3/flash-attention/releases/download/v2.6.3/flash_attn-2.6.3+cu123torch2.4.1cxx11abiFALSE-cp310-cp310-win_amd64.whl

if (-not (Test-Path $BASE)) { New-Item -ItemType Directory -Force -Path $BASE | Out-Null }
git clone https://github.com/bmwas/InfiniteTalk $PROJECT
cd $PROJECT

pip install "huggingface_hub[cli]"
huggingface-cli download MeiGen-AI/Wan2.1-I2V-14B-480P --local-dir weights/Wan2.1-I2V-14B-480P
huggingface-cli download MeiGen-AI/chinese-wav2vec2-base --local-dir weights/chinese-wav2vec2-base
huggingface-cli download MeiGen-AI/InfiniteTalk --local-dir weights/InfiniteTalk

Write-Host "InfiniteTalk installed at $PROJECT"
Write-Host "Total weights size ~40GB. Adjust paths if needed."
```

</details>

---

## 2. 把 InfiniteTalk 包装成 HTTP API

InfiniteTalk 原生是 CLI / ComfyUI 节点,本项目期望一个 **HTTP 服务**。下面是一份**最小可用** FastAPI wrapper(`server.py`),放到 InfiniteTalk 项目根目录:

```python
"""server.py — Wrap InfiniteTalk as HTTP API for nce-video-pipeline.

POST /api/digital-human/generate
    multipart: reference_image (image), audio (audio)
    form: resolution=480p|720p, mode=image2video|video2video
    -> {"task_id": "..."}

GET  /api/digital-human/status/{task_id}
    -> {"status": "pending|running|done|failed", "progress": 0-100, "video_url": "...", "error": "..."}

GET  /api/digital-human/download/{task_id}
    -> mp4 binary
"""
from __future__ import annotations
import asyncio, uuid, subprocess, shutil
from pathlib import Path
from typing import Dict
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse

ROOT = Path(__file__).parent.resolve()
RUNS = ROOT / "runs"
RUNS.mkdir(exist_ok=True)

app = FastAPI(title="InfiniteTalk HTTP API")

TASKS: Dict[str, dict] = {}


async def _run_infinitetalk(task_id: str, image: Path, audio: Path, resolution: str) -> None:
    out_dir = RUNS / task_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_video = out_dir / "output.mp4"

    TASKS[task_id]["status"] = "running"
    TASKS[task_id]["progress"] = 5
    try:
        # 调用 InfiniteTalk CLI(以官方 generate.py 为例,实际命令以你装的版本为准)
        cmd = [
            "python", str(ROOT / "generate.py"),
            "--ref_image", str(image),
            "--audio", str(audio),
            "--resolution", "480" if resolution == "480p" else "720",
            "--output", str(out_video),
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        # 简单的进度心跳(实际你可以读 stderr 解析 InfiniteTalk 的进度日志)
        TASKS[task_id]["progress"] = 50
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            TASKS[task_id].update(
                status="failed", error=stderr.decode("utf-8", errors="replace")[-2000:]
            )
            return
        TASKS[task_id].update(status="done", progress=100, video_path=str(out_video))
    except Exception as e:
        TASKS[task_id].update(status="failed", error=repr(e))


@app.post("/api/digital-human/generate")
async def generate(
    reference_image: UploadFile = File(...),
    audio: UploadFile = File(...),
    resolution: str = Form("480p"),
    mode: str = Form("image2video"),
):
    task_id = uuid.uuid4().hex[:12]
    work = RUNS / task_id
    work.mkdir(parents=True, exist_ok=True)

    img_path = work / reference_image.filename
    aud_path = work / audio.filename
    img_path.write_bytes(await reference_image.read())
    aud_path.write_bytes(await audio.read())

    TASKS[task_id] = {"status": "pending", "progress": 0, "video_path": None, "error": None}
    asyncio.create_task(_run_infinitetalk(task_id, img_path, aud_path, resolution))
    return {"task_id": task_id}


@app.get("/api/digital-human/status/{task_id}")
async def status(task_id: str):
    if task_id not in TASKS:
        raise HTTPException(404, "task not found")
    s = TASKS[task_id]
    return {
        "status": s.get("status", "pending"),
        "progress": s.get("progress", 0),
        "error": s.get("error"),
    }


@app.get("/api/digital-human/download/{task_id}")
async def download(task_id: str):
    s = TASKS.get(task_id)
    if not s or s.get("status") != "done":
        raise HTTPException(404, "task not ready or not found")
    return FileResponse(s["video_path"], media_type="video/mp4", filename="output.mp4")


@app.get("/healthz")
async def healthz():
    return {"ok": True, "active": sum(1 for t in TASKS.values() if t.get("status") in ("pending", "running"))}
```

启动:

```bash
cd D:\ai\InfiniteTalk
conda activate infinitetalk
uvicorn server:app --host 0.0.0.0 --port 8000
```

> **关键点**:`server.py` 里的 `generate.py` 命令需要根据你装的 InfiniteTalk 版本调整(命令行参数可能不同)。如果你用 ComfyUI workflow,可以改成调用 ComfyUI 的 API(`/queue` + `/history`)。

---

## 3. 配置 nce-video-pipeline 接入

在 nce-video-pipeline 项目的 `.env` 中:

```env
INFINITETALK_API_URL=http://你的GPU服务器IP:8000
INFINITETALK_RESOLUTION=480p
INFINITETALK_REFERENCE_IMAGE=assets/avatar.png
INFINITETALK_TIMEOUT=1800
```

然后准备一张 `assets/avatar.png`(1024×1024 正脸照片),重启服务即可。

---

## 4. 验证联调

```bash
# 在 GPU 服务器上检查服务起来了
curl http://localhost:8000/healthz

# 在 nce-video-pipeline 这边触发一集
python -m scripts.generate_all --range 1-1
```

`output/<project_id>/digital_human.mp4` 应该是生成的数字人视频(约 30-90 秒后完成,看 GPU 性能 + 音频长度)。

---

## 5. 常见问题

| 问题 | 解决 |
|------|------|
| `InfiniteTalk task timed out` | 调大 `INFINITETALK_TIMEOUT`(1 分钟视频通常需要 5-15 分钟渲染) |
| `flash-attn install failed` | 用预编译 wheel(见上面 PowerShell 脚本) |
| `CUDA out of memory` | 显存不够,改 `INFINITETALK_RESOLUTION=480p` 或减少 `motion_frames` |
| `ConnectionRefused` | 检查 GPU 服务器防火墙是否放行 8000 端口 |
| HuggingFace 下载慢 | `$env:HF_ENDPOINT='https://hf-mirror.com'` |

---

## 6. 安全建议

- 不要把 GPU 服务器的 8000 端口直接暴露公网,**用 Cloudflare Tunnel / Tailscale / WireGuard 内网穿透**
- 可在 `server.py` 加 `Authorization: Bearer <token>` 验证,在 `.env` 设 `INFINITETALK_API_KEY`
