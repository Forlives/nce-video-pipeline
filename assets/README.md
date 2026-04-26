# Assets 素材目录

本目录存放视频拼接需要的静态资源。**项目内默认不带任何二进制素材**(避免仓库膨胀),你需要按下表自行准备:

| 文件 | 用途 | 推荐规格 |
|------|------|----------|
| `background.png` | 静态背景图(无数字人模式时使用) | 1280×720 PNG/JPG,亮度适中,留出底部 200px 给字幕 |
| `bgm.mp3` | 背景音乐(可选) | 轻音乐 / 学习场景音乐,**版权干净**(无版权 / CC0 / 你拥有授权) |
| `avatar.png` | 数字人参考图(InfiniteTalk 模式) | 1024×1024 正脸照片,SD 生成或自有授权肖像 |

## 快速准备(推荐)

### 选项 1:用 Stable Diffusion 生成(本地)
```bash
# 推荐 prompt(背景图)
"library bookshelves, soft warm lighting, cinematic, blurred background, 16:9, 1280x720"

# 推荐 prompt(虚拟形象 avatar)
"young Asian female teacher, friendly smile, looking at camera, soft studio lighting, professional portrait, photorealistic, 1024x1024"
```

### 选项 2:CC0 公共素材站
- 背景:**Unsplash** / **Pixabay** / **Pexels**(搜索 "library", "study room", "modern classroom")
- BGM:**YouTube Audio Library** / **Pixabay Music** / **freemusicarchive.org**(搜索 "calm study music")
- Avatar:**ThisPersonDoesNotExist.com**(免费,但确认你不打算商用其肖像或自承担风险)

### 选项 3:用现成的占位图(测试用)
```bash
# 命令行下载一张占位图(测试可用)
curl https://picsum.photos/1280/720 -o assets/background.png
```

## 文件就位后

只要文件存在,`pipeline` 会自动检测并使用。
如果 `infinitetalk_api_url` 已配置,会优先调用数字人;否则回退到背景图模式。
