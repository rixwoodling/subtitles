#!/usr/bin/env python3

import argparse
import glob
import os
import subprocess
import sys


def run(cmd):

    print(f"\n[RUNNING] {' '.join(cmd)}\n")

    result = subprocess.run(cmd)

    if result.returncode != 0:
        print("\nCommand failed.")
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

    latest = max(mp3_files, key=os.path.getctime)

    return latest


def transcribe(audio_file, model, output_format):

    run([
        "mlx_whisper",
        audio_file,
        "--language",
        "zh",
        "--model",
        model,
        "--output-format",
        output_format
    ])


def main():

    parser = argparse.ArgumentParser(
        description="YouTube/audio transcriber using MLX Whisper"
    )

    parser.add_argument(
        "input",
        help="YouTube URL or local audio/video file"
    )

    parser.add_argument(
        "--model",
        default="mlx-community/whisper-medium-mlx",
        help="MLX Whisper model"
    )

    parser.add_argument(
        "--output-format",
        default="all",
        choices=["txt", "json", "srt", "vtt", "all"],
        help="Output format"
    )

    args = parser.parse_args()

    source = args.input

    if source.startswith("http://") or source.startswith("https://"):

        print("\nDownloading YouTube audio...")
        audio_file = download_audio(source)

    else:

        if not os.path.exists(source):

            print(f"\nFile not found: {source}")
            sys.exit(1)

        audio_file = source

    print(f"\nUsing audio file: {audio_file}")

    print("\nTranscribing with MLX Whisper...")

    transcribe(
        audio_file,
        args.model,
        args.output_format
    )

    print("\nDone.")

    generated = []

    for ext in ["txt", "json", "srt", "vtt"]:

        files = glob.glob(f"*.{ext}")

        if files:

            newest = max(files, key=os.path.getctime)
            generated.append(newest)

    if generated:

        print("\nGenerated files:\n")

        for f in generated:
            print(f"  {f}")


if __name__ == "__main__":
    main()
