#!/usr/bin/env python3

import argparse
import json
import os
import sys
from difflib import SequenceMatcher


HELP_TEXT = """
ASR+OCR_merger.py

Merge:
- MLX Whisper ASR transcripts
- EasyOCR subtitle transcripts

Uses:
- timestamps
- OCR confidence
- ASR confidence
- text similarity

to intelligently choose the best subtitle line.

--------------------------------------------------
INSTALLATION
--------------------------------------------------

No extra packages required.

Uses only:
- Python standard library

--------------------------------------------------
USAGE
--------------------------------------------------

python3 ASR+OCR_merger.py \
OCR/OCR.json \
ASR/ASR.json

Optional:

python3 ASR+OCR_merger.py \
OCR/OCR.json \
ASR/ASR.json \
--output merged.json \
--min-ocr-confidence 0.60 \
--time-window 1.5

--------------------------------------------------
OUTPUT
--------------------------------------------------

merged.json
merged.txt
merged.srt
merged.vtt

Contains:
- merged subtitles
- timestamps
- chosen source
- confidence
- reasoning

--------------------------------------------------
MERGE STRATEGY
--------------------------------------------------

1. Find OCR entries near ASR timestamps
2. Compare text similarity
3. Prefer OCR when:
    - OCR confidence is high
    - OCR text is longer/better
4. Prefer ASR when:
    - OCR confidence is weak
    - OCR looks corrupted
5. Preserve ASR timing

--------------------------------------------------
NOTES
--------------------------------------------------

- OCR is usually better for:
    proper nouns
    subtitles
    names
    signs

- ASR is usually better for:
    spoken grammar
    sentence flow
    fast dialogue

- Best results happen when:
    OCR + ASR agree

--------------------------------------------------
"""


def print_compact_help():

    print("""
usage: ASR+OCR_merger.py [-h]
                         [--output OUTPUT]
                         [--min-ocr-confidence MIN_OCR_CONFIDENCE]
                         [--time-window TIME_WINDOW]
                         ocr_json asr_json

Merge OCR + ASR transcripts intelligently

positional arguments:
  ocr_json             OCR JSON file
  asr_json             ASR JSON file

options:
  -h, --help
  --output OUTPUT
  --min-ocr-confidence MIN_OCR_CONFIDENCE
  --time-window TIME_WINDOW
""")


def load_json(path):

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_asr(data):

    if isinstance(data, dict):
        segments = data.get("segments", [])
    else:
        segments = data

    normalized = []

    for seg in segments:

        confidence = 0.0

        if "avg_logprob" in seg:

            confidence = max(
                0.0,
                min(
                    1.0,
                    1.0 + (seg["avg_logprob"] / 5.0)
                )
            )

        normalized.append({
            "start": seg.get("start", 0),
            "end": seg.get("end", 0),
            "text": seg.get("text", "").strip(),
            "confidence": confidence,
            "source": "ASR"
        })

    return normalized


def normalize_ocr(data):

    normalized = []

    for seg in data:

        start = seg.get("seconds", 0)

        duration = seg.get(
            "duration",
            1
        )

        normalized.append({
            "start": start,
            "end": start + duration,
            "text": seg.get("text", "").strip(),
            "confidence": seg.get(
                "confidence",
                0
            ),
            "source": "OCR"
        })

    return normalized


def similarity(a, b):

    return SequenceMatcher(
        None,
        a,
        b
    ).ratio()


def looks_like_garbage(text):

    if not text:
        return True

    stripped = text.strip()

    if len(stripped) <= 1:
        return True

    junk_chars = set([
        ".",
        ",",
        "?",
        "!",
        "=",
        "-",
        "_",
        "/"
    ])

    if all(c in junk_chars for c in stripped):
        return True

    return False


def find_matching_ocr(
        asr_seg,
        ocr_segments,
        time_window):

    matches = []

    for ocr in ocr_segments:

        delta = abs(
            ocr["start"]
            - asr_seg["start"]
        )

        if delta <= time_window:
            matches.append(ocr)

    return matches


def choose_best(
        asr_seg,
        ocr_matches,
        min_ocr_confidence):

    best = {
        "start": asr_seg["start"],
        "end": asr_seg["end"],
        "text": asr_seg["text"],
        "source": "ASR",
        "confidence": asr_seg["confidence"],
        "reason": "default_asr"
    }

    best_score = 0

    for ocr in ocr_matches:

        if looks_like_garbage(
                ocr["text"]):
            continue

        sim = similarity(
            asr_seg["text"],
            ocr["text"]
        )

        score = 0

        score += sim * 50
        score += ocr["confidence"] * 40

        if len(ocr["text"]) > len(
                asr_seg["text"]):
            score += 5

        if (
            ocr["confidence"]
            >= min_ocr_confidence
        ):
            score += 10

        if score > best_score:

            best_score = score

            if (
                ocr["confidence"]
                >= asr_seg["confidence"]
            ):

                best = {
                    "start": asr_seg["start"],
                    "end": asr_seg["end"],
                    "text": ocr["text"],
                    "source": "OCR",
                    "confidence":
                        ocr["confidence"],
                    "reason": (
                        f"ocr_conf="
                        f"{ocr['confidence']:.2f} "
                        f"similarity="
                        f"{sim:.2f}"
                    )
                }

    return best


def merge(
        asr_segments,
        ocr_segments,
        min_ocr_confidence,
        time_window):

    merged = []

    for asr_seg in asr_segments:

        ocr_matches = find_matching_ocr(
            asr_seg,
            ocr_segments,
            time_window
        )

        best = choose_best(
            asr_seg,
            ocr_matches,
            min_ocr_confidence
        )

        merged.append(best)

    return merged


def seconds_to_timestamp(seconds):

    hours = int(seconds // 3600)

    minutes = int(
        (seconds % 3600) // 60
    )

    secs = seconds % 60

    return (
        f"{hours:02d}:"
        f"{minutes:02d}:"
        f"{secs:06.3f}"
    )


def save_json(data, filename):

    with open(
        filename,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )


def save_txt(data, filename):

    with open(
        filename,
        "w",
        encoding="utf-8"
    ) as f:

        for seg in data:

            conf = seg.get(
                "confidence",
                0
            )

            f.write(
                f"[conf={conf:.2f}] "
                f"{seg['text']}\n"
            )


def save_srt(data, filename):

    with open(
        filename,
        "w",
        encoding="utf-8"
    ) as f:

        for idx, seg in enumerate(
                data,
                start=1):

            start = (
                seconds_to_timestamp(
                    seg["start"]
                ).replace(".", ",")
            )

            end = (
                seconds_to_timestamp(
                    seg["end"]
                ).replace(".", ",")
            )

            conf = seg.get(
                "confidence",
                0
            )

            text = seg["text"]

            f.write(f"{idx}\n")

            f.write(
                f"{start} --> "
                f"{end}\n"
            )

            f.write(
                f"[conf={conf:.2f}] "
                f"{text}\n\n"
            )


def save_vtt(data, filename):

    with open(
        filename,
        "w",
        encoding="utf-8"
    ) as f:

        f.write("WEBVTT\n\n")

        for seg in data:

            start = seconds_to_timestamp(
                seg["start"]
            )

            end = seconds_to_timestamp(
                seg["end"]
            )

            conf = seg.get(
                "confidence",
                0
            )

            text = seg["text"]

            f.write(
                f"{start} --> "
                f"{end}\n"
            )

            f.write(
                f"[conf={conf:.2f}] "
                f"{text}\n\n"
            )


def print_merged(data):

    print("\nMerged Transcript:\n")

    for seg in data:

        start = seconds_to_timestamp(
            seg["start"]
        )

        end = seconds_to_timestamp(
            seg["end"]
        )

        conf = seg.get(
            "confidence",
            0
        )

        source = seg.get(
            "source",
            "?"
        )

        text = seg["text"]

        print(
            f"[{start} --> {end}] "
            f"[conf={conf:.2f}] "
            f"[{source}] "
            f"{text}"
        )


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
        "ocr_json"
    )

    parser.add_argument(
        "asr_json"
    )

    parser.add_argument(
        "--output",
        default="merged.json"
    )

    parser.add_argument(
        "--min-ocr-confidence",
        type=float,
        default=0.60
    )

    parser.add_argument(
        "--time-window",
        type=float,
        default=1.5
    )

    args = parser.parse_args()

    if not os.path.exists(
            args.ocr_json):

        print(
            f"\nOCR JSON not found:\n"
            f"{args.ocr_json}\n"
        )

        sys.exit(1)

    if not os.path.exists(
            args.asr_json):

        print(
            f"\nASR JSON not found:\n"
            f"{args.asr_json}\n"
        )

        sys.exit(1)

    print("\nLoading transcripts...")

    ocr_data = load_json(
        args.ocr_json
    )

    asr_data = load_json(
        args.asr_json
    )

    print("\nNormalizing OCR...")

    ocr_segments = normalize_ocr(
        ocr_data
    )

    print("\nNormalizing ASR...")

    asr_segments = normalize_asr(
        asr_data
    )

    print("\nMerging intelligently...")

    merged = merge(
        asr_segments,
        ocr_segments,
        args.min_ocr_confidence,
        args.time_window
    )

    base = os.path.splitext(
        args.output
    )[0]

    save_json(
        merged,
        f"{base}.json"
    )

    save_txt(
        merged,
        f"{base}.txt"
    )

    save_srt(
        merged,
        f"{base}.srt"
    )

    save_vtt(
        merged,
        f"{base}.vtt"
    )

    print_merged(
        merged
    )

    print("\nDone.")

    print("\nGenerated:\n")

    print(f"  {base}.json")
    print(f"  {base}.txt")
    print(f"  {base}.srt")
    print(f"  {base}.vtt")


if __name__ == "__main__":
    main()
