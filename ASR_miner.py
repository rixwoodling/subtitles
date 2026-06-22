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
"""

cc = OpenCC("s2t")


def print_compact_help():
    print("""
usage: ASR_miner.py [-h]
                    [--model MODEL]
                    input
MLX Whisper ASR transcriber
""")


def run(cmd):
    print(f"\n[RUNNING] {' '.join(cmd)}\n")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print("\nCommand failed.")
        sys.exit(1)


def handle_help():
    if len(sys.argv) == 1:
        print_compact_help()
        sys.exit(0)

    if "-h" in sys.argv or "--help" in sys.argv:
        print(HELP_TEXT)
        sys.exit(0)


def parse_arguments():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("input")
    parser.add_argument(
        "--model",
        default="mlx-community/whisper-medium-mlx"
    )
    return parser.parse_args()


def verify_dependencies():
    required = ["yt-dlp", "ffmpeg", "mlx_whisper"]
    missing = [tool for tool in required if shutil.which(tool) is None]

    if missing:
        print("\nMissing dependencies:\n")
        for tool in missing:
            print(f"  {tool}")
        print("\nInstall missing tools first.")
        sys.exit(1)


def initialize():
    handle_help()
    args = parse_arguments()
    verify_dependencies()
    return args


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

    return max(mp3_files, key=os.path.getctime)


def acquire_audio(args):
    source = args.input

    if source.startswith(("http://", "https://")):
        print("\nDownloading YouTube audio...")
        return download_audio(source)

    if not os.path.exists(source):
        print(f"\nFile not found: {source}")
        sys.exit(1)

    return source


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


def transcribe_audio(audio_file, model):
    print(f"\nUsing audio file: {audio_file}")
    print("\nTranscribing with MLX Whisper...")
    transcribe(audio_file, model)


def newest_json():
    files = glob.glob("*.json")
    return max(files, key=os.path.getctime) if files else None


def locate_transcript():
    json_path = newest_json()

    if not json_path:
        print("\nNo JSON output found.")
        sys.exit(1)

    return json_path


def seconds_to_timestamp(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02}:{minutes:02}:{secs:06.3f}"


def logprob_to_confidence(logprob):
    if logprob is None:
        return 0.0

    confidence = math.exp(logprob)
    confidence = max(0.0, min(1.0, confidence))
    return round(confidence, 2)


def convert_traditional(text):
    return cc.convert(text)


def process_json(json_path):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    segments = data.get("segments", [])

    txt_lines = []
    log_lines = []
    srt_blocks = []
    vtt_blocks = ["WEBVTT\n"]

    for i, segment in enumerate(segments, start=1):
        start = segment.get("start", 0)
        end = segment.get("end", 0)

        text = convert_traditional(
            segment.get("text", "").strip()
        )

        confidence = logprob_to_confidence(
            segment.get("avg_logprob")
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

        srt_blocks.append(
            f"{i}\n"
            f"{start_ts.replace('.', ',')} --> "
            f"{end_ts.replace('.', ',')}\n"
            f"{text}\n"
        )

        vtt_blocks.append(
            f"{start_ts} --> {end_ts}\n"
            f"{text}\n"
        )

    with open("ASR.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(txt_lines))

    with open("ASR.log", "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines))

    with open("ASR.srt", "w", encoding="utf-8") as f:
        f.write("\n".join(srt_blocks))

    with open("ASR.vtt", "w", encoding="utf-8") as f:
        f.write("\n".join(vtt_blocks))

    with open("ASR.json", "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )


def generate_outputs(json_path):
    print("\nProcessing transcript...")
    process_json(json_path)


def display_results():
    print("\nGenerated files:\n")

    for output in (
        "ASR.txt",
        "ASR.json",
        "ASR.srt",
        "ASR.vtt",
        "ASR.log"
    ):
        if os.path.exists(output):
            print(f"  {output}")

    print("\nDone.")


def main():
    args = initialize()
    audio_file = acquire_audio(args)
    transcribe_audio(audio_file, args.model)
    json_path = locate_transcript()
    generate_outputs(json_path)
    display_results()


if __name__ == "__main__":
    main()
