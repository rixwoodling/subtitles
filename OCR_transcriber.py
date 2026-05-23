#!/usr/bin/env python3

"""
OCR_transcriber.py

EasyOCR subtitle transcriber for:
- YouTube videos
- Local video files
- Hardcoded subtitles
- Traditional Chinese / English subtitles
"""

import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections import defaultdict, deque

import cv2
import easyocr
from rapidfuzz import fuzz


SHORT_HELP = """
usage: OCR_transcriber.py [-h] [--fps FPS]
                          [--crop-y CROP_Y]
                          [--crop-height CROP_HEIGHT]
                          [--scale-factor SCALE_FACTOR]
                          [--min-confidence MIN_CONFIDENCE]
                          [--min-likelihood MIN_LIKELIHOOD]
                          [--min-persistence MIN_PERSISTENCE]
                          [--languages LANGUAGES [LANGUAGES ...]]
                          [--output-format {txt,json,srt,all}]
                          input

EasyOCR subtitle transcriber

positional arguments:
  input                 YouTube URL or local video

options:
  -h, --help            show detailed help message
  --fps FPS             Frames sampled per second
  --crop-y CROP_Y       Subtitle crop start position
  --crop-height HEIGHT  Subtitle crop height
  --scale-factor SCALE  Upscale subtitle region
  --min-confidence VAL  OCR confidence filter
  --min-likelihood VAL  Subtitle likelihood filter
  --min-persistence N   Repeated subtitle threshold
  --languages LANG ...  OCR language list
  --output-format TYPE  txt, json, srt, all
"""


LONG_HELP = """
OCR_transcriber.py

EasyOCR subtitle transcriber for:
- YouTube videos
- Local video files
- Hardcoded subtitles
- Traditional Chinese / English subtitles

--------------------------------------------------
INSTALLATION
--------------------------------------------------

1. Install system tools (macOS):

    brew install ffmpeg yt-dlp

2. Create / activate virtual environment:

    python3 -m venv venv
    source venv/bin/activate

3. Install Python packages:

    pip install easyocr rapidfuzz opencv-python

Optional but recommended:

    pip install torch torchvision

--------------------------------------------------
USAGE
--------------------------------------------------

YouTube video:

    python3 OCR_transcriber.py \\
    "https://www.youtube.com/watch?v=VIDEO_ID"

Local file:

    python3 OCR_transcriber.py video.mp4

Recommended subtitle settings:

    python3 OCR_transcriber.py \\
    "https://www.youtube.com/watch?v=VIDEO_ID" \\
    --fps 1 \\
    --crop-y 0.75 \\
    --crop-height 0.25 \\
    --scale-factor 4 \\
    --min-confidence 0.35

Generate only SRT:

    python3 OCR_transcriber.py \\
    video.mp4 \\
    --output-format srt

--------------------------------------------------
FLAG EXPLANATIONS
--------------------------------------------------

--fps FLOAT
    Default: 1.0

    Frames sampled per second.

    Higher:
    - better subtitle timing
    - catches fast subtitle changes
    - slower processing

    Lower:
    - faster
    - may miss subtitles

--------------------------------------------------

--crop-y FLOAT
    Default: 0.75

    Vertical subtitle crop start.

    Lower:
    - captures more screen
    - more OCR garbage

    Higher:
    - tighter subtitle focus
    - risk cutting subtitles

--------------------------------------------------

--crop-height FLOAT
    Default: 0.25

    Height of subtitle crop area.

    Lower:
    - cleaner OCR
    - may clip subtitles

    Higher:
    - safer subtitle capture
    - more background noise

--------------------------------------------------

--scale-factor INTEGER
    Default: 4

    Upscales subtitle region before OCR.

    Higher:
    - better readability
    - slower
    - more RAM usage

--------------------------------------------------

--min-confidence FLOAT
    Default: 0.35

    OCR confidence threshold.

    Lower:
    - more subtitle guesses
    - more garbage

    Higher:
    - cleaner results
    - may skip valid subtitles

    Typical:
    0.20 - 0.60

--------------------------------------------------

--min-likelihood FLOAT
    Default: 5

    Filters unlikely subtitle text.

    Removes:
    - random symbols
    - repeated junk
    - OCR nonsense

--------------------------------------------------

--min-persistence INTEGER
    Default: 1

    Subtitle must appear this many times.

    Higher:
    - less flicker garbage
    - may skip quick subtitles

--------------------------------------------------

--languages
    Default:
    ch_tra en

    Examples:

    Traditional Chinese:
        ch_tra

    Simplified Chinese:
        ch_sim

    Japanese:
        ja

    Korean:
        ko

    English:
        en

--------------------------------------------------

--output-format
    Default: all

    txt
        plain text

    json
        structured OCR metadata

    srt
        subtitle file

    all
        generate everything

--------------------------------------------------

OUTPUTS
--------------------------------------------------

.txt
    Plain subtitle text

.json
    OCR metadata:
    - timestamps
    - confidence
    - subtitle likelihood

.srt
    Subtitle file

--------------------------------------------------

NOTES
--------------------------------------------------

- First EasyOCR run downloads AI models
- EasyOCR works MUCH better than Tesseract
  for subtitle OCR
- OCR still struggles with:
    - fast motion
    - heavy compression
    - stylized fonts
    - overlapping graphics

--------------------------------------------------
"""


REQUIRED_TOOLS = [
    "ffmpeg",
    "yt-dlp"
]


def check_dependencies():
    missing = [t for t in REQUIRED_TOOLS if shutil.which(t) is None]

    if missing:
        print("\nMissing required system tools:\n")

        for tool in missing:
            print(f"  - {tool}")

        print("\nInstall with:\n")
        print(f"brew install {' '.join(missing)}\n")

        sys.exit(1)


def run(cmd):
    print(f"\n[RUNNING] {' '.join(cmd)}\n")

    result = subprocess.run(cmd)

    if result.returncode != 0:
        print("\nCommand failed.")
        sys.exit(1)


def download_video(url):
    run([
        "yt-dlp",
        "-f", "b[ext=mp4]",
        "-o", "%(title)s.%(ext)s",
        url
    ])

    mp4_files = glob.glob("*.mp4")

    if not mp4_files:
        print("\nNo MP4 downloaded.")
        sys.exit(1)

    return max(mp4_files, key=os.path.getctime)


def extract_frames(video_file, output_dir, fps,
                   crop_y, crop_height, scale_factor):

    vf = (
        f"fps={fps},"
        f"crop=in_w:in_h*{crop_height}:0:in_h*{crop_y},"
        f"scale=iw*{scale_factor}:ih*{scale_factor}"
    )

    run([
        "ffmpeg",
        "-i", video_file,
        "-vf", vf,
        f"{output_dir}/frame_%06d.jpg"
    ])


def normalize_text(text):
    return " ".join(text.strip().split())


def chinese_ratio(text):
    chinese = sum(
        1 for c in text
        if '\u4e00' <= c <= '\u9fff'
    )

    return chinese / len(text) if text else 0


def repeated_pattern_ratio(text):
    if len(text) < 6:
        return 0

    chunks = [
        text[i:i+2]
        for i in range(0, len(text), 2)
    ]

    return 1 - (len(set(chunks)) / len(chunks))


def weird_symbol_ratio(text):
    weird = sum(
        1 for c in text
        if not (
            '\u4e00' <= c <= '\u9fff'
            or c.isalnum()
            or c in " ，。！？：「」『』（）()[]-—,.!? "
        )
    )

    return weird / len(text) if text else 0


def subtitle_likelihood(text):
    text = normalize_text(text)

    if not text:
        return -999

    score = 0
    length = len(text)

    if 4 <= length <= 45:
        score += 15
    elif length < 2:
        score -= 25
    elif length > 80:
        score -= 20

    score += chinese_ratio(text) * 30
    score -= repeated_pattern_ratio(text) * 40
    score -= weird_symbol_ratio(text) * 30

    return score


def preprocess_image(image_path):
    return cv2.imread(image_path)


def ocr_easyocr(reader, image):
    results = reader.readtext(
        image,
        detail=1,
        paragraph=False
    )

    parsed = []

    for r in results:
        text = normalize_text(r[1])
        conf = float(r[2])

        if text:
            parsed.append({
                "text": text,
                "confidence": conf
            })

    return parsed


def combine_rows(rows):
    return normalize_text(
        " ".join(r["text"] for r in rows)
    )


def seconds_to_srt(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)

    return (
        f"{hours:02d}:"
        f"{minutes:02d}:"
        f"{secs:02d},"
        f"{millis:03d}"
    )


def save_txt(entries, filename):
    with open(filename, "w", encoding="utf-8") as f:
        for e in entries:
            f.write(e["text"] + "\n")


def save_json(entries, filename):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(
            entries,
            f,
            ensure_ascii=False,
            indent=2
        )


def save_srt(entries, filename):
    with open(filename, "w", encoding="utf-8") as f:

        for idx, e in enumerate(entries, start=1):

            start = e["seconds"]
            end = start + e["duration"]

            f.write(f"{idx}\n")

            f.write(
                f"{seconds_to_srt(start)} --> "
                f"{seconds_to_srt(end)}\n"
            )

            f.write(e["text"] + "\n\n")


def merge_entries(entries):
    if not entries:
        return []

    merged = []
    current = entries[0]

    for nxt in entries[1:]:

        similarity = fuzz.ratio(
            current["text"],
            nxt["text"]
        )

        if similarity > 92:

            current["duration"] += nxt["duration"]

            current["confidence"] = max(
                current["confidence"],
                nxt["confidence"]
            )

        else:
            merged.append(current)
            current = nxt

    merged.append(current)

    return merged


def main():

    if len(sys.argv) == 1:
        print(SHORT_HELP)
        sys.exit(1)

    if "-h" in sys.argv or "--help" in sys.argv:
        print(LONG_HELP)
        sys.exit(0)

    check_dependencies()

    parser = argparse.ArgumentParser(
        add_help=False
    )

    parser.add_argument("input")

    parser.add_argument(
        "--fps",
        type=float,
        default=1.0
    )

    parser.add_argument(
        "--crop-y",
        type=float,
        default=0.75
    )

    parser.add_argument(
        "--crop-height",
        type=float,
        default=0.25
    )

    parser.add_argument(
        "--scale-factor",
        type=int,
        default=4
    )

    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.35
    )

    parser.add_argument(
        "--min-likelihood",
        type=float,
        default=5
    )

    parser.add_argument(
        "--min-persistence",
        type=int,
        default=1
    )

    parser.add_argument(
        "--languages",
        nargs="+",
        default=["ch_tra", "en"]
    )

    parser.add_argument(
        "--output-format",
        default="all",
        choices=[
            "txt",
            "json",
            "srt",
            "all"
        ]
    )

    args = parser.parse_args()

    print("\nLoading EasyOCR...\n")

    reader = easyocr.Reader(
        args.languages
    )

    source = args.input

    if source.startswith("http://") or source.startswith("https://"):

        print("\nDownloading video...\n")

        video_file = download_video(source)

    else:

        if not os.path.exists(source):
            print(f"\nFile not found: {source}")
            sys.exit(1)

        video_file = source

    print(f"\nUsing video:\n{video_file}")

    with tempfile.TemporaryDirectory() as temp_dir:

        print("\nExtracting frames...\n")

        extract_frames(
            video_file,
            temp_dir,
            args.fps,
            args.crop_y,
            args.crop_height,
            args.scale_factor
        )

        frames = sorted([
            f for f in os.listdir(temp_dir)
            if f.endswith(".jpg")
        ])

        entries = []

        persistence = defaultdict(int)

        recent = deque(maxlen=5)

        for idx, frame in enumerate(frames):

            frame_path = os.path.join(
                temp_dir,
                frame
            )

            image = preprocess_image(frame_path)

            if image is None:
                continue

            rows = ocr_easyocr(
                reader,
                image
            )

            rows = [
                r for r in rows
                if r["confidence"]
                >= args.min_confidence
            ]

            if not rows:
                continue

            text = combine_rows(rows)

            if not text:
                continue

            likelihood = subtitle_likelihood(text)

            if likelihood < args.min_likelihood:
                continue

            duplicate = False

            for old in recent:

                similarity = fuzz.ratio(
                    text,
                    old
                )

                if similarity > 95:
                    duplicate = True
                    break

            recent.append(text)

            persistence[text] += 1

            if persistence[text] < args.min_persistence:
                continue

            if duplicate:
                continue

            timestamp = idx / args.fps

            avg_conf = (
                sum(r["confidence"] for r in rows)
                / len(rows)
            )

            entry = {
                "seconds": round(timestamp, 3),
                "duration": round(1 / args.fps, 3),
                "text": text,
                "confidence": round(avg_conf, 3),
                "likelihood": round(likelihood, 2)
            }

            entries.append(entry)

            print(
                f"[{timestamp:.2f}] "
                f"[conf={avg_conf:.2f}] "
                f"{text}"
            )

        entries = merge_entries(entries)

    base = os.path.splitext(
        os.path.basename(video_file)
    )[0]

    if args.output_format in ["txt", "all"]:
        save_txt(entries, f"{base}.txt")

    if args.output_format in ["json", "all"]:
        save_json(entries, f"{base}.json")

    if args.output_format in ["srt", "all"]:
        save_srt(entries, f"{base}.srt")

    print("\nDone.\n")

    print("Generated:\n")

    if args.output_format in ["txt", "all"]:
        print(f"  {base}.txt")

    if args.output_format in ["json", "all"]:
        print(f"  {base}.json")

    if args.output_format in ["srt", "all"]:
        print(f"  {base}.srt")


if __name__ == "__main__":
    main()
