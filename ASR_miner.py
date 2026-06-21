#!/usr/bin/env python3
import argparse
import glob
import json
import math
import os
import shutil
import subprocess
import sys
from opencc import OpenCC

HELP_TEXT = """
ASR_miner.py
MLX Whisper subtitle transcriber for:
- YouTube videos
- Local audio/video files
- Mandarin speech transcription
- Traditional Chinese output
Features:
- Traditional Chinese conversion
- confidence scoring
- TXT / JSON / SRT / VTT / LOG outputs
- readable transcript logs
- YouTube downloading
- MLX Whisper acceleration (Apple Silicon)
--------------------------------------------------
INSTALLATION
--------------------------------------------------
1. Install system tools (macOS):
    brew install ffmpeg yt-dlp
2. Create / activate virtual environment:
    python3 -m venv venv
    source venv/bin/activate
3. Install Python packages:
    pip install mlx-whisper
    pip install opencc-python-reimplemented
Optional but recommended:
    pip install torch torchvision
--------------------------------------------------
USAGE
--------------------------------------------------
YouTube video:
    python3 ASR_miner.py \
    "https://www.youtube.com/watch?v=VIDEO_ID"
Local file:
    python3 ASR_miner.py video.mp4
Custom model:
    python3 ASR_miner.py \
    video.mp4 \
    --model mlx-community/whisper-large-v3-mlx
--------------------------------------------------
OUTPUTS
--------------------------------------------------
ASR.txt
    Plain transcript text
ASR.json
    Structured transcript data
ASR.srt
    Subtitle file
ASR.vtt
    WebVTT subtitle file
ASR.log
    Human-readable timestamped transcript
--------------------------------------------------
NOTES
--------------------------------------------------
- Output converted to Traditional Chinese
- Requires Apple Silicon for best performance
- First run downloads Whisper model
- Confidence scores derived from Whisper logprobs
- Much better than OCR for spoken-only dialogue
--------------------------------------------------
"""

cc = OpenCC('s2t')

def print_compact_help():
    print("""
usage: ASR_miner.py [-h]
                           [--model MODEL]
                           input
MLX Whisper ASR transcriber
positional arguments:
  input                 YouTube URL or local audio/video
options:
  -h, --help
  --model MODEL
""")

def run(cmd):
    print(f"\n[RUNNING] {' '.join(cmd)}\n")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print("\nCommand failed.")
        sys.exit(1)

def check_dependencies():
    required = [
        "yt-dlp",
        "ffmpeg",
        "mlx_whisper"
    ]
    missing = []
    for tool in required:
        if shutil.which(tool) is None:
            missing.append(tool)
    if missing:
        print("\nMissing dependencies:\n")
        for tool in missing:
            print(f"  {tool}")
        print("\nInstall missing tools first.")
        sys.exit(1)

def download_audio(url):
    run([
        "yt-dlp",
        "-x",
        "--audio-format",
        "mp3",
        "--output",
        "%(title)s.%(ext)s",
        url
    ])
    mp3_files = glob.glob("*.mp3")
    if not mp3_files:
        print("\nNo MP3 file found.")
        sys.exit(1)
    return max(
        mp3_files,
        key=os.path.getctime
    )

def newest_json():
    files = glob.glob("*.json")
    if not files:
        return None
    return max(
        files,
        key=os.path.getctime
    )

def seconds_to_timestamp(seconds):
    hours = int(seconds // 3600)
    minutes = int(
        (seconds % 3600) // 60
    )
    secs = seconds % 60
    return (
        f"{hours:02}:{minutes:02}:"
        f"{secs:06.3f}"
    )

def logprob_to_confidence(logprob):
    if logprob is None:
        return 0.0
    confidence = math.exp(logprob)
    confidence = max(
        0.0,
        min(1.0, confidence)
    )
    return round(confidence, 2)

def convert_traditional(text):
    return cc.convert(text)

def process_json(json_path):
    with open(
        json_path,
        "r",
        encoding="utf-8"
    ) as f:
        data = json.load(f)
    segments = data.get(
        "segments",
        []
    )
    txt_lines = []
    log_lines = []
    srt_blocks = []
    vtt_blocks = ["WEBVTT\n"]
    for i, segment in enumerate(segments, start=1):
        start = segment.get("start", 0)
        end = segment.get("end", 0)
        text = segment.get(
            "text",
            ""
        ).strip()
        text = convert_traditional(text)
        logprob = segment.get(
            "avg_logprob",
            None
        )
        confidence = logprob_to_confidence(
            logprob
        )
        segment["text"] = text
        segment["confidence"] = confidence
        txt_lines.append(text)
        start_ts = seconds_to_timestamp(start)
        end_ts = seconds_to_timestamp(end)
        log_line = (
            f"[{start_ts} --> {end_ts}] "
            f"[conf={confidence:.2f}] "
            f"{text}"
        )
        log_lines.append(log_line)
        print(log_line)
        srt_start = start_ts.replace(".", ",")
        srt_end = end_ts.replace(".", ",")
        srt_blocks.append(
            f"{i}\n"
            f"{srt_start} --> {srt_end}\n"
            f"{text}\n"
        )
        vtt_blocks.append(
            f"{start_ts} --> {end_ts}\n"
            f"{text}\n"
        )
    with open(
        "ASR.txt",
        "w",
        encoding="utf-8"
    ) as f:
        f.write(
            "\n".join(txt_lines)
        )
    with open(
        "ASR.log",
        "w",
        encoding="utf-8"
    ) as f:
        f.write(
            "\n".join(log_lines)
        )
    with open(
        "ASR.srt",
        "w",
        encoding="utf-8"
    ) as f:
        f.write(
            "\n".join(srt_blocks)
        )
    with open(
        "ASR.vtt",
        "w",
        encoding="utf-8"
    ) as f:
        f.write(
            "\n".join(vtt_blocks)
        )
    with open(
        "ASR.json",
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )

def transcribe(audio_file, model):
    run([
        "mlx_whisper",
        audio_file,
        "--language",
        "zh",
        "--model",
        model,
        "--output-format",
        "json",
        "--word-timestamps",
        "True",
        "--hallucination-silence-threshold",
        "1"
    ])

def main():
    if len(sys.argv) == 1:
        print_compact_help()
        sys.exit(0)
    if (
        "-h" in sys.argv
        or "--help" in sys.argv
    ):
        print(HELP_TEXT)
        sys.exit(0)
    parser = argparse.ArgumentParser(
        add_help=False
    )
    parser.add_argument(
        "input"
    )
    parser.add_argument(
        "--model",
        default=(
            "mlx-community/"
            "whisper-medium-mlx"
        )
    )
    args = parser.parse_args()
    check_dependencies()
    source = args.input
    if (
        source.startswith("http://")
        or source.startswith("https://")
    ):
        print(
            "\nDownloading YouTube audio..."
        )
        audio_file = download_audio(
            source
        )
    else:
        if not os.path.exists(source):
            print(
                f"\nFile not found: "
                f"{source}"
            )
            sys.exit(1)
        audio_file = source
    print(
        f"\nUsing audio file: "
        f"{audio_file}"
    )
    print(
        "\nTranscribing with MLX Whisper..."
    )
    transcribe(
        audio_file,
        args.model
    )
    json_path = newest_json()
    if not json_path:
        print(
            "\nNo JSON output found."
        )
        sys.exit(1)
    print(
        "\nProcessing transcript..."
    )
    process_json(json_path)
    print("\nGenerated files:\n")
    outputs = [
        "ASR.txt",
        "ASR.json",
        "ASR.srt",
        "ASR.vtt",
        "ASR.log"
    ]
    for output in outputs:
        if os.path.exists(output):
            print(f"  {output}")
    print("\nDone.")

if __name__ == "__main__":
    main()
