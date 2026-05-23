# submerge

Subtitle tools for OCR, ASR, and intelligent transcript merging.

`submerge` is a local-first subtitle toolkit for:
- extracting hardcoded subtitles with OCR
- transcribing speech with Whisper ASR
- intelligently merging OCR + ASR into cleaner subtitles

Built for:
- YouTube videos
- local media files
- multilingual subtitles
- noisy dialogue
- Traditional Chinese content
- subtitle restoration workflows

---

# Features

## OCR Transcription
Extract hardcoded subtitles directly from video frames using EasyOCR.

Supports:
- Traditional Chinese
- English
- outlined subtitles
- low-resolution YouTube video
- embedded subtitles

Outputs:
- `.txt`
- `.json`
- `.srt`

---

## ASR Transcription
Generate subtitles directly from speech audio using MLX Whisper.

Supports:
- YouTube URLs
- local media files
- Apple Silicon acceleration
- word timestamps
- confidence metrics
- hallucination mitigation

Outputs:
- `.txt`
- `.json`
- `.srt`
- `.vtt`

---

## Intelligent OCR + ASR Fusion
Merge OCR subtitles with ASR transcripts using:
- timestamps
- confidence scoring
- text similarity
- arbitration logic

Goal:
- cleaner subtitles
- fewer hallucinations
- better proper nouns
- improved subtitle accuracy

Outputs:
- `.json`
- `.txt`
- `.srt`
- `.vtt`

---

# Included Scripts

| Script | Purpose |
|---|---|
| `OCR_transcriber.py` | OCR hardcoded subtitles from video |
| `ASR_transcriber.py` | Speech transcription using MLX Whisper |
| `ASR+OCR_merger.py` | Merge OCR + ASR intelligently |

---

# Requirements

## Supported Platforms

### OCR Scripts
`OCR_transcriber.py` works on:
- macOS
- Linux
- Windows

### ASR Scripts
`ASR_transcriber.py` currently uses:
- `mlx-whisper`

which requires:
- Apple Silicon
- macOS
- MLX support

Recommended:
- M1 / M2 / M3 / M4 Macs

Best performance:
- M3 / M4 systems

---

# Required System Tools

Install these first.

## macOS

```bash
brew install ffmpeg yt-dlp
```

## Ubuntu / Debian

```bash
sudo apt install ffmpeg yt-dlp
```

---

# Python Requirements

Install inside a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

Then install Python dependencies:

```bash
pip install -r requirements.txt
```

Current `requirements.txt`:

```txt
easyocr
mlx-whisper
opencv-python
rapidfuzz
torch
torchvision
```

---

# Important Notes

## MLX Whisper Limitation

`mlx-whisper` is Apple Silicon specific.

If using:
- Intel Mac
- Linux
- Windows
- NVIDIA GPU systems

you may want to replace:
- `mlx-whisper`

with:
- `faster-whisper`
- `openai-whisper`

Future versions of `submerge` may support multiple ASR backends.

---

# First Run Downloads

The first run will automatically download:
- EasyOCR AI models
- Whisper AI models

This is normal.

Model downloads can be several GB depending on:
- OCR language packs
- Whisper model size

---

# Usage

---

# OCR Transcriber

Extract hardcoded subtitles from video.

## YouTube Example

```bash
python3 OCR_transcriber.py \
"https://www.youtube.com/watch?v=VIDEO_ID"
```

## Local File Example

```bash
python3 OCR_transcriber.py video.mp4
```

## Recommended Settings

```bash
python3 OCR_transcriber.py \
video.mp4 \
--fps 1 \
--crop-y 0.75 \
--crop-height 0.25 \
--scale-factor 4 \
--min-confidence 0.35 \
--min-persistence 1
```

---

# OCR Example Output

```text
[102.00] [conf=0.93] 我第一次去東京的時候超緊張
[104.00] [conf=0.98] 結果發現根本很多台灣人
[106.00] [conf=0.74] 而且店員其實都很有耐心
[108.00] [conf=0.99] 只是電車真的有點複雜
[110.00] [conf=0.88] 我那天直接坐錯方向
[112.00] [conf=0.95] 然後多花了快四十分鐘
[114.00] [conf=0.81] 不過現在回想起來很好笑
[116.00] [conf=1.00] 下次還是會想再去
```

### OCR Notes

- Better at visible subtitle text
- Better at:
    - names
    - signs
    - subtitle wording
- More sensitive to:
    - low resolution
    - motion blur
    - stylized fonts

---

# ASR Transcriber

Generate subtitles directly from speech.

## YouTube Example

```bash
python3 ASR_transcriber.py \
"https://www.youtube.com/watch?v=VIDEO_ID"
```

## Local File Example

```bash
python3 ASR_transcriber.py video.mp4
```

## Recommended Settings

```bash
python3 ASR_transcriber.py \
video.mp4 \
--model mlx-community/whisper-large-v3-mlx \
--temperature 0 \
--best-of 5 \
--condition-on-previous-text False \
--no-speech-threshold 0.6 \
--word-timestamps True \
--hallucination-silence-threshold 2
```

---

# ASR Example Output

```text
[00:01:42.120 --> 00:01:43.860] [conf=0.91] 我覺得大阪真的很好逛
[00:01:43.860 --> 00:01:45.420] [conf=0.91] 而且東西也沒有想像中貴
[00:01:45.420 --> 00:01:47.080] [conf=0.88] 台灣現在很多咖啡廳都超貴
[00:01:47.080 --> 00:01:48.920] [conf=0.88] 去日本反而覺得輕鬆很多
[00:01:48.920 --> 00:01:50.200] [conf=0.82] 主要還是那邊氣氛不一樣
[00:01:50.200 --> 00:01:51.600] [conf=0.82] 會想一直走路一直逛
[00:01:51.600 --> 00:01:52.840] [conf=0.79] 但真的很容易買太多
```

### ASR Notes

- Strong sentence flow
- Natural grammar
- Sometimes weak on:
    - names
    - brands
    - subtitle-specific wording

---

# OCR + ASR Merger

Fuse OCR subtitles and ASR transcripts together.

## Merge Example

```bash
python3 ASR+OCR_merger.py \
OCR/OCR.json \
ASR/ASR.json
```

## Strict OCR Preference

```bash
python3 ASR+OCR_merger.py \
OCR/OCR.json \
ASR/ASR.json \
--min-ocr-confidence 0.80
```

---

# Merge Example Output

```text
[00:04:12.200 --> 00:04:14.540] [conf=0.96] [ASR] 我覺得現在年輕人真的很愛出國
[00:04:14.540 --> 00:04:16.120] [conf=0.98] [OCR] 尤其日本跟韓國
[00:04:16.120 --> 00:04:18.620] [conf=0.94] [ASR] 因為機票有時候比國旅還便宜
[00:04:18.620 --> 00:04:20.440] [conf=1.00] [OCR] 住宿反而比較舒服
[00:04:20.440 --> 00:04:22.800] [conf=0.92] [ASR] 而且可以順便體驗不同文化
[00:04:22.800 --> 00:04:24.620] [conf=0.99] [OCR] 很多人一年會出國兩三次
```

### Merge Notes

- `[OCR]` means OCR won arbitration
- `[ASR]` means Whisper ASR won arbitration
- Confidence values help debug merge decisions
- Fusion often improves:
    - subtitle accuracy
    - proper nouns
    - subtitle clarity

---

# Example Workflow

## 1. OCR hardcoded subtitles

```bash
python3 OCR_transcriber.py video.mp4
```

## 2. Generate ASR transcript

```bash
python3 ASR_transcriber.py video.mp4
```

## 3. Merge both transcripts

```bash
python3 ASR+OCR_merger.py \
OCR.json \
ASR.json
```

---

# Why OCR + ASR?

ASR and OCR each have different strengths.

| System | Good At | Weak At |
|---|---|---|
| OCR | visible subtitles, names, signs | stylized fonts, motion |
| ASR | speech flow, grammar | noisy audio, proper nouns |

Combining both systems often produces better subtitles than either alone.

---

# Use Cases

## Restore Hardcoded Subtitles
Recover subtitles from videos with burned-in captions.

---

## Improve ASR Accuracy
Use OCR to correct:
- names
- places
- brands
- signs
- subtitles

---

## YouTube Archival
Generate subtitles for:
- interviews
- podcasts
- travel videos
- documentaries
- livestreams

---

## Traditional Chinese Subtitle Workflows
Useful for:
- Taiwanese YouTube
- Mandarin subtitle extraction
- mixed Chinese/English subtitles

---

## Local-First Subtitle Generation
No cloud APIs required.

Runs locally using:
- EasyOCR
- MLX Whisper
- FFmpeg

---

# Notes

- First EasyOCR run downloads OCR models
- First MLX Whisper run downloads Whisper models
- Apple Silicon strongly recommended for ASR speed
- OCR quality depends heavily on subtitle clarity
- Low-resolution video may still produce OCR artifacts

---

# Future Ideas

Potential future additions:
- subtitle cleanup
- translation
- speaker detection
- chapter extraction
- subtitle alignment
- diarization
- subtitle search indexing

---

# License

MIT License
