#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chương trình tự động phân tích khoảng lặng và cắt file audio thành các câu tiếng Anh riêng biệt.
Tối ưu cho Windows, sử dụng FFmpeg.

Hỗ trợ:
- Bài 1 (4 BAI 1.mp3): 13 câu -> 4 BAI 1-1.mp3 đến 4 BAI 1-13.mp3
- Bài 2 (4 BAI 2.mp3): 12 câu -> 4 BAI 2-1.mp3 đến 4 BAI 2-12.mp3

Tác giả: Antigravity AI Pair Programmer
"""

import os
import sys
import json
import subprocess
import argparse
from typing import List, Dict, Tuple, Optional

# ==============================================================================
# DỮ LIỆU CÁC BÀI HỌC
# ==============================================================================

LESSONS_DATA = {
    1: {
        "title": "Bài 1: Nguyên âm /i:/ vs /ɪ/",
        "default_filename": "4 BAI 1.mp3",
        "prefix": "4 BAI 1",
        "sentences": [
            "You can see a lot of geese in the field in my hometown.",
            "I often leave my Japanese book in the bedroom.",
            "Eating ice-cream is not good for your teeth.",
            "I hope that I can beat my Chinese competitor.",
            "Do you often go sightseeing with your friends in autumn?",
            "I love the peaceful life near the beach.",
            "If my younger brother receives two free tickets tomorrow, he will feel very glad.",
            "A goal without a plan is just a wish.",
            "Health is not simply the absence of sickness.",
            "Men talk of killing time while time quitely kills them.",
            "Life is just a mirror and what you see out there, you must see inside of you.",
            "It is difficult to say what is impossible, for the dream of yesterday is the hope of today and the reality of tomorrow.",
            "To avoid criticism: do nothing, say nothing, be nothing."
        ],
        "authors": {
            8: "Antoine de Saint – Exupery",
            11: "Wally Famous Amos",
            12: "Robert H. Goddard"
        },
        "timings_full": [
            (1,  0.00,  3.50),
            (2,  5.00,  8.35),
            (3,  8.75, 11.60),
            (4, 11.90, 15.00),
            (5, 16.35, 19.65),
            (6, 19.90, 22.85),
            (7, 23.30, 28.45),
            (8, 28.70, 33.30),
            (9, 33.85, 37.60),
            (10, 39.65, 43.60),
            (11, 44.20, 51.90),
            (12, 52.40, 62.05),
            (13, 62.30, 67.85)
        ],
        "timings_quote_only": [
            (1,  0.00,  3.50),
            (2,  5.00,  8.35),
            (3,  8.75, 11.60),
            (4, 11.90, 15.00),
            (5, 16.35, 19.65),
            (6, 19.90, 22.85),
            (7, 23.30, 28.45),
            (8, 28.70, 31.65),
            (9, 33.85, 37.60),
            (10, 39.65, 43.60),
            (11, 44.20, 49.30),
            (12, 52.40, 59.55),
            (13, 62.30, 67.85)
        ]
    },
    2: {
        "title": "Bài 2: Nguyên âm /u:/ vs /ʊ/",
        "default_filename": "4 BAI 2.mp3",
        "prefix": "4 BAI 2",
        "sentences": [
            "I like fruit juice and soup.",
            "He knew all the food in the room.",
            "Whose suitcase is this?",
            "My student likes blue and I do, too.",
            "I only hope that my health will improve soon.",
            "Next Tuesday afternoon, I will prove that I know how to play the flute.",
            "The statue on the avenue is near the swimming pool.",
            "We stood to watch football.",
            "I would like to read a good cookery book.",
            "The box is full of sugar.",
            "I took a look at the pullover.",
            "You should push the door to come in! Don’t pull it!"
        ],
        "authors": {},
        "timings_full": [
            (1,  0.00,  2.15),
            (2,  2.20,  4.55),
            (3,  4.65,  6.80),
            (4,  6.90,  9.80),
            (5,  9.95, 13.05),
            (6, 13.25, 18.20),
            (7, 18.45, 21.75),
            (8, 21.80, 24.00),
            (9, 24.15, 26.90),
            (10, 27.15, 29.25),
            (11, 29.40, 31.50),
            (12, 31.55, 35.60)
        ],
        "timings_quote_only": [
            (1,  0.00,  2.15),
            (2,  2.20,  4.55),
            (3,  4.65,  6.80),
            (4,  6.90,  9.80),
            (5,  9.95, 13.05),
            (6, 13.25, 18.20),
            (7, 18.45, 21.75),
            (8, 21.80, 24.00),
            (9, 24.15, 26.90),
            (10, 27.15, 29.25),
            (11, 29.40, 31.50),
            (12, 31.55, 35.60)
        ]
    }
}

# Hỗ trợ tương thích ngược cho Bài 1
SENTENCES_TEXT = LESSONS_DATA[1]["sentences"]
SENTENCES_AUTHORS = LESSONS_DATA[1]["authors"]
TIMINGS_FULL = LESSONS_DATA[1]["timings_full"]
TIMINGS_QUOTE_ONLY = LESSONS_DATA[1]["timings_quote_only"]

# ==============================================================================
# HÀM HỖ TRỢ HỆ THỐNG
# ==============================================================================

def find_ffmpeg_executable() -> str:
    """Tìm đường dẫn thực thi của ffmpeg."""
    try:
        res = subprocess.run(["where.exe", "ffmpeg"], capture_output=True, text=True)
        if res.returncode == 0:
            lines = [l.strip() for l in res.stdout.strip().splitlines() if l.strip()]
            if lines: return lines[0]
    except Exception:
        pass

    common_paths = [
        r"C:\Users\Windows\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg.Shared_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build-shared\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        r"C:\ffmpeg\bin\ffmpeg.exe"
    ]
    for p in common_paths:
        if os.path.exists(p):
            return p
    return "ffmpeg"

def find_ffplay_executable() -> str:
    """Tìm đường dẫn thực thi của ffplay."""
    try:
        res = subprocess.run(["where.exe", "ffplay"], capture_output=True, text=True)
        if res.returncode == 0:
            lines = [l.strip() for l in res.stdout.strip().splitlines() if l.strip()]
            if lines: return lines[0]
    except Exception:
        pass
    return "ffplay"

def detect_audio_for_lesson(lesson_num: int) -> Optional[str]:
    """Tìm file audio theo số bài (1, 2, ...)."""
    cfg = LESSONS_DATA.get(lesson_num)
    if not cfg:
        return None
    candidates = [
        os.path.join("sounds", cfg["default_filename"]),
        os.path.join(".", cfg["default_filename"]),
        os.path.join("sounds", cfg["default_filename"].replace(" ", "_")),
        os.path.join(".", cfg["default_filename"].replace(" ", "_"))
    ]
    for c in candidates:
        if os.path.isfile(c):
            return os.path.abspath(c)
    return None

def detect_input_audio(preferred_path: Optional[str] = None) -> Optional[str]:
    """Tự động tìm file audio nguồn."""
    if preferred_path and os.path.isfile(preferred_path):
        return os.path.abspath(preferred_path)

    # Ưu tiên Bài 1 rồi Bài 2
    for l_num in [1, 2]:
        p = detect_audio_for_lesson(l_num)
        if p: return p

    if os.path.isdir("sounds"):
        for f in os.listdir("sounds"):
            if f.lower().endswith((".mp3", ".wav", ".m4a")) and not f.startswith("4 BAI 1-") and not f.startswith("4 BAI 2-"):
                return os.path.abspath(os.path.join("sounds", f))
    return None

def guess_lesson_from_filename(filename: str) -> int:
    """Đoán số bài học từ tên file."""
    base = os.path.basename(filename).lower()
    if "bai 2" in base or "bai_2" in base or "bai2" in base:
        return 2
    return 1

def get_sentence_configs(lesson_num: int = 1, profile: str = "full", custom_config_path: Optional[str] = None) -> List[Dict]:
    """Lấy danh sách cấu hình mốc thời gian của bài học."""
    if custom_config_path and os.path.isfile(custom_config_path):
        with open(custom_config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    cfg = LESSONS_DATA.get(lesson_num, LESSONS_DATA[1])
    prefix = cfg["prefix"]
    raw_timings = cfg["timings_full"] if profile == "full" else cfg["timings_quote_only"]

    items = []
    for num, start, end in raw_timings:
        text = cfg["sentences"][num - 1] if num - 1 < len(cfg["sentences"]) else f"Câu {num}"
        author = cfg["authors"].get(num, None) if profile == "full" else None
        items.append({
            "lesson": lesson_num,
            "index": num,
            "filename": f"{prefix}-{num}.mp3",
            "start": round(start, 2),
            "end": round(end, 2),
            "duration": round(end - start, 2),
            "text": text,
            "author": author
        })
    return items

def play_preview(audio_path: str, start: float, end: float, ffplay_bin: str = "ffplay"):
    """Phát thử đoạn audio bằng ffplay."""
    duration = end - start
    print(f"[*] Đang nghe thử: {start:.2f}s -> {end:.2f}s (thời lượng: {duration:.2f}s)...")
    cmd = [
        ffplay_bin,
        "-ss", str(start),
        "-t", str(duration),
        "-autoexit",
        "-nodisp",
        "-loglevel", "quiet",
        audio_path
    ]
    subprocess.run(cmd)

def cut_single_sentence(
    input_audio: str,
    output_audio: str,
    start: float,
    end: float,
    ffmpeg_bin: str = "ffmpeg",
    bitrate: str = "192k"
) -> bool:
    """Cắt 1 đoạn audio bằng FFmpeg và mã hóa lại sang MP3 chất lượng cao."""
    os.makedirs(os.path.dirname(os.path.abspath(output_audio)), exist_ok=True)
    cmd = [
        ffmpeg_bin,
        "-y",
        "-ss", f"{start:.3f}",
        "-to", f"{end:.3f}",
        "-i", input_audio,
        "-c:a", "libmp3lame",
        "-b:a", bitrate,
        "-loglevel", "error",
        output_audio
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"[!] Lỗi khi cắt {output_audio}: {res.stderr}")
        return False
    return True

def print_preview_table(items: List[Dict]):
    """Hiển thị bảng xem trước các câu."""
    print("=" * 95)
    print(f"{'STT':<4} | {'Tên file đích':<16} | {'Bắt đầu':<8} | {'Kết thúc':<8} | {'Thời lượng':<10} | {'Nội dung câu'}")
    print("-" * 95)
    for it in items:
        note = f" (+ {it['author']})" if it.get("author") else ""
        text_disp = it['text'] + note
        if len(text_disp) > 42:
            text_disp = text_disp[:39] + "..."
        print(f"{it['index']:<4} | {it['filename']:<16} | {it['start']:<7.2f}s | {it['end']:<7.2f}s | {it['duration']:<9.2f}s | {text_disp}")
    print("=" * 95)

def export_all_sentences(
    input_audio: str,
    output_dir: str,
    items: List[Dict],
    ffmpeg_bin: str = "ffmpeg",
    bitrate: str = "192k",
    report_filename: str = "cut_report.txt"
) -> Tuple[List[str], str]:
    """Cắt và xuất toàn bộ các câu ra thư mục đầu ra kèm báo cáo."""
    os.makedirs(output_dir, exist_ok=True)
    success_files = []
    report_lines = []

    lesson_num = items[0].get("lesson", 1) if items else 1
    title_str = LESSONS_DATA.get(lesson_num, {}).get("title", f"Bài {lesson_num}")

    report_lines.append("================================================================================")
    report_lines.append(f"                    BÁO CÁO CẮT AUDIO: {title_str.upper()}                       ")
    report_lines.append("================================================================================")
    report_lines.append(f"File nguồn: {input_audio}")
    report_lines.append(f"Thư mục xuất: {os.path.abspath(output_dir)}")
    report_lines.append(f"Tổng số câu: {len(items)}")
    report_lines.append(f"Định dạng xuất: MP3 (Bitrate: {bitrate})")
    report_lines.append("--------------------------------------------------------------------------------")
    report_lines.append(f"{'STT':<4} | {'Tên file':<16} | {'Bắt đầu':<8} | {'Kết thúc':<8} | {'Thời lượng':<10} | {'Dung lượng':<10} | {'Trạng thái'}")
    report_lines.append("--------------------------------------------------------------------------------")

    print(f"\n[*] Bắt đầu cắt và xuất {len(items)} câu vào thư mục: '{output_dir}'...")

    for it in items:
        out_path = os.path.join(output_dir, it['filename'])
        ok = cut_single_sentence(input_audio, out_path, it['start'], it['end'], ffmpeg_bin, bitrate)
        
        status = "Thành công" if ok else "LỖI"
        size_str = "0 B"
        if ok and os.path.exists(out_path):
            size_bytes = os.path.getsize(out_path)
            size_str = f"{size_bytes / 1024:.1f} KB"
            if size_bytes > 0:
                success_files.append(out_path)
            else:
                status = "File rỗng"

        report_lines.append(
            f"{it['index']:<4} | {it['filename']:<16} | {it['start']:<7.2f}s | {it['end']:<7.2f}s | {it['duration']:<9.2f}s | {size_str:<10} | {status}"
        )
        print(f"  [+] Đã tạo: {it['filename']} ({it['duration']:.2f}s - {size_str}) -> {status}")

    report_lines.append("--------------------------------------------------------------------------------")
    report_lines.append(f"Tổng kết: {len(success_files)}/{len(items)} file hợp lệ.")
    report_lines.append("Danh sách chi tiết nội dung từng câu:")
    for it in items:
        author_info = f" [Tác giả: {it['author']}]" if it.get("author") else ""
        report_lines.append(f"  {it['index']:2d}. {it['filename']}: \"{it['text']}\"{author_info}")
    report_lines.append("================================================================================")

    report_content = "\n".join(report_lines)
    report_file = os.path.join(output_dir, report_filename)
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report_content)

    print(f"\n[*] Đã xuất xong! Báo cáo chi tiết đã được lưu tại: {report_file}")
    return success_files, report_file

def main():
    parser = argparse.ArgumentParser(description="Tự động cắt file audio thành các câu tiếng Anh riêng biệt.")
    parser.add_argument("--input", "-i", help="Đường dẫn file audio nguồn")
    parser.add_argument("--bai", "-b", type=int, choices=[1, 2], help="Chọn số bài học (1 hoặc 2)")
    parser.add_argument("--all", "-a", action="store_true", help="Tự động cắt tất cả các bài có file audio trong sounds/")
    parser.add_argument("--output", "-o", default=os.path.join("sounds", "cut_sentences"), help="Thư mục xuất kết quả (mặc định: sounds/cut_sentences)")
    parser.add_argument("--profile", "-p", choices=["full", "quote_only"], default="full", help="Profile cắt: 'full' hoặc 'quote_only'")
    parser.add_argument("--config", "-c", help="Đường dẫn file JSON cấu hình điểm cắt tùy chỉnh")
    parser.add_argument("--preview", action="store_true", help="Chỉ xem bảng điểm cắt dự kiến, không cắt")
    parser.add_argument("--play", type=int, help="Nghe thử câu thứ N")
    parser.add_argument("--bitrate", default="192k", help="Bitrate MP3 xuất (mặc định: 192k)")

    args = parser.parse_args()

    ffmpeg_bin = find_ffmpeg_executable()
    ffplay_bin = find_ffplay_executable()

    # Chế độ cắt tất cả các bài
    if args.all:
        for l_num in [1, 2]:
            audio = detect_audio_for_lesson(l_num)
            if audio and os.path.isfile(audio):
                print(f"\n{'='*70}\n[*] XỬ LÝ BÀI {l_num}: {audio}\n{'='*70}")
                items = get_sentence_configs(lesson_num=l_num, profile=args.profile)
                print_preview_table(items)
                rep_name = f"cut_report_bai{l_num}.txt"
                export_all_sentences(audio, args.output, items, ffmpeg_bin, args.bitrate, rep_name)
        return

    # Nhận diện bài học và file audio
    input_audio = args.input
    lesson_num = args.bai

    if input_audio:
        if not lesson_num:
            lesson_num = guess_lesson_from_filename(input_audio)
    else:
        if lesson_num:
            input_audio = detect_audio_for_lesson(lesson_num)
        else:
            input_audio = detect_input_audio()
            if input_audio:
                lesson_num = guess_lesson_from_filename(input_audio)

    if not input_audio or not os.path.isfile(input_audio):
        print("[!] LỖI: Không tìm thấy file audio nguồn! Vui lòng chỉ định bằng --input <đường dẫn>.")
        sys.exit(1)

    lesson_num = lesson_num or 1
    items = get_sentence_configs(lesson_num=lesson_num, profile=args.profile, custom_config_path=args.config)

    print(f"[*] File audio nguồn: {input_audio}")
    print(f"[*] Bài học         : {LESSONS_DATA.get(lesson_num, {}).get('title', f'Bài {lesson_num}')}")
    print(f"[*] Thư mục đầu ra  : {os.path.abspath(args.output)}")
    print(f"[*] Profile cắt     : {'Đầy đủ' if args.profile == 'full' else 'Chỉ câu nói'}")

    if args.preview:
        print_preview_table(items)
        return

    if args.play is not None:
        if 1 <= args.play <= len(items):
            item = items[args.play - 1]
            play_preview(input_audio, item['start'], item['end'], ffplay_bin)
        else:
            print(f"[!] Số thứ tự câu phải từ 1 đến {len(items)}")
        return

    print_preview_table(items)
    rep_name = f"cut_report_bai{lesson_num}.txt" if lesson_num != 1 else "cut_report.txt"
    success_files, report_file = export_all_sentences(input_audio, args.output, items, ffmpeg_bin, args.bitrate, rep_name)

    if len(success_files) == len(items):
        print(f"\n[✓] HOÀN TẤT: Đã cắt thành công trọn vẹn đủ {len(items)}/{len(items)} file MP3!")
        print(f"[✓] Vị trí lưu: {os.path.abspath(args.output)}")
        print(f"[✓] Báo cáo tại: {report_file}")
    else:
        print(f"\n[!] CẢNH BÁO: Chỉ tạo thành công {len(success_files)}/{len(items)} file.")

if __name__ == "__main__":
    main()
