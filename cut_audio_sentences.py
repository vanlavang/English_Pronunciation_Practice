#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chương trình tự động phân tích khoảng lặng và cắt file audio thành 13 câu tiếng Anh riêng biệt.
Tối ưu cho Windows, sử dụng FFmpeg.

Tác giả: Antigravity AI Pair Programmer
Mục tiêu: Cắt file '4 BAI 1.mp3' thành 13 file '4 BAI 1-1.mp3' -> '4 BAI 1-13.mp3'
"""

import os
import sys
import json
import subprocess
import argparse
from typing import List, Dict, Tuple, Optional

# Danh sách 13 câu chuẩn theo thứ tự audio
SENTENCES_TEXT = [
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
]

# Danh sách tên tác giả đọc kèm ở cuối các câu trích dẫn
SENTENCES_AUTHORS = {
    8: "Antoine de Saint – Exupery",
    11: "Wally Famous Amos",
    12: "Robert H. Goddard"
}

# Các mốc thời gian chuẩn xác đã phân tích qua phân tích sóng âm & khoảng lặng (FFmpeg silencedetect)
# Profile 'full': Bao gồm cả tên tác giả (phù hợp với dữ liệu bài học Unit 1)
TIMINGS_FULL = [
    (1,  0.00,  3.50),   # Câu 1
    (2,  5.00,  8.35),   # Câu 2
    (3,  8.75, 11.60),   # Câu 3
    (4, 11.90, 15.00),   # Câu 4
    (5, 16.35, 19.65),   # Câu 5
    (6, 19.90, 22.85),   # Câu 6
    (7, 23.30, 28.45),   # Câu 7
    (8, 28.70, 33.30),   # Câu 8 (+ Antoine de Saint-Exupery)
    (9, 33.85, 37.60),   # Câu 9
    (10, 39.65, 43.60),  # Câu 10
    (11, 44.20, 51.90),  # Câu 11 (+ Wally Famous Amos)
    (12, 52.40, 62.05),  # Câu 12 (+ Robert H. Goddard)
    (13, 62.30, 67.85),  # Câu 13
]

# Profile 'quote_only': Chỉ chứa nội dung câu nói, không bao gồm tên tác giả
TIMINGS_QUOTE_ONLY = [
    (1,  0.00,  3.50),
    (2,  5.00,  8.35),
    (3,  8.75, 11.60),
    (4, 11.90, 15.00),
    (5, 16.35, 19.65),
    (6, 19.90, 22.85),
    (7, 23.30, 28.45),
    (8, 28.70, 31.65),   # Dừng trước khi đọc tên tác giả
    (9, 33.85, 37.60),
    (10, 39.65, 43.60),
    (11, 44.20, 49.30),  # Dừng trước khi đọc tên tác giả
    (12, 52.40, 59.55),  # Dừng trước khi đọc tên tác giả
    (13, 62.30, 67.85),
]

def find_ffmpeg_executable() -> str:
    """Tìm đường dẫn thực thi của ffmpeg."""
    # 1. Thử lệnh trong PATH
    try:
        res = subprocess.run(["where.exe", "ffmpeg"], capture_output=True, text=True)
        if res.returncode == 0:
            lines = [l.strip() for l in res.stdout.strip().splitlines() if l.strip()]
            if lines:
                return lines[0]
    except Exception:
        pass

    # 2. Thử các đường dẫn phổ biến trên Windows
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
    """Tìm đường dẫn thực thi của ffplay để nghe thử."""
    try:
        res = subprocess.run(["where.exe", "ffplay"], capture_output=True, text=True)
        if res.returncode == 0:
            lines = [l.strip() for l in res.stdout.strip().splitlines() if l.strip()]
            if lines:
                return lines[0]
    except Exception:
        pass
    return "ffplay"

def detect_input_audio(preferred_path: Optional[str] = None) -> Optional[str]:
    """Tự động tìm file audio nguồn."""
    if preferred_path and os.path.isfile(preferred_path):
        return os.path.abspath(preferred_path)

    # Các vị trí mặc định thường gặp
    candidates = [
        os.path.join("sounds", "4 BAI 1.mp3"),
        os.path.join(".", "4 BAI 1.mp3"),
        os.path.join("sounds", "4_BAI_1.mp3"),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return os.path.abspath(c)

    # Tìm file mp3 bất kỳ trong thư mục sounds
    if os.path.isdir("sounds"):
        for f in os.listdir("sounds"):
            if f.lower().endswith((".mp3", ".wav", ".m4a")):
                return os.path.abspath(os.path.join("sounds", f))

    return None

def analyze_silence_ffmpeg(audio_path: str, ffmpeg_bin: str = "ffmpeg", noise_db: str = "-30dB", min_duration: float = 0.3) -> List[Tuple[float, float, float]]:
    """Phân tích các khoảng lặng trong file audio bằng FFmpeg silencedetect."""
    cmd = [
        ffmpeg_bin,
        "-i", audio_path,
        "-af", f"silencedetect=noise={noise_db}:d={min_duration}",
        "-f", "null",
        "-"
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    lines = res.stderr.splitlines()

    silences = []
    current_start = None

    for line in lines:
        if "silence_start:" in line:
            parts = line.split("silence_start:")
            if len(parts) > 1:
                try:
                    current_start = float(parts[1].strip().split()[0])
                except ValueError:
                    pass
        elif "silence_end:" in line and current_start is not None:
            parts = line.split("silence_end:")
            if len(parts) > 1:
                sub = parts[1].split("|")
                try:
                    end_val = float(sub[0].strip().split()[0])
                    dur_val = end_val - current_start
                    silences.append((current_start, end_val, dur_val))
                except ValueError:
                    pass
            current_start = None

    return silences

def get_sentence_configs(profile: str = "full", custom_config_path: Optional[str] = None) -> List[Dict]:
    """Lấy danh sách mốc thời gian và thông tin của 13 câu."""
    if custom_config_path and os.path.isfile(custom_config_path):
        with open(custom_config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data

    raw_timings = TIMINGS_FULL if profile == "full" else TIMINGS_QUOTE_ONLY
    items = []
    for num, start, end in raw_timings:
        text = SENTENCES_TEXT[num - 1]
        author = SENTENCES_AUTHORS.get(num, None)
        items.append({
            "index": num,
            "filename": f"4 BAI 1-{num}.mp3",
            "start": round(start, 2),
            "end": round(end, 2),
            "duration": round(end - start, 2),
            "text": text,
            "author": author if profile == "full" else None
        })
    return items

def save_config(items: List[Dict], filepath: str):
    """Lưu cấu hình mốc thời gian ra file JSON."""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    print(f"[*] Đã lưu cấu hình điểm cắt vào: {filepath}")

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
    """Hiển thị bảng xem trước 13 câu."""
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
    bitrate: str = "192k"
) -> Tuple[List[str], str]:
    """Cắt và xuất toàn bộ 13 câu ra thư mục đầu ra kèm báo cáo."""
    os.makedirs(output_dir, exist_ok=True)
    success_files = []
    report_lines = []

    report_lines.append("================================================================================")
    report_lines.append("                    BÁO CÁO CẮT AUDIO 13 CÂU TIẾNG ANH                          ")
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
    report_file = os.path.join(output_dir, "cut_report.txt")
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report_content)

    print(f"\n[*] Đã xuất xong! Báo cáo chi tiết đã được lưu tại: {report_file}")
    return success_files, report_file

def interactive_mode(input_audio: str, items: List[Dict], output_dir: str, ffmpeg_bin: str, ffplay_bin: str):
    """Chế độ tương tác dòng lệnh để nghe thử và chỉnh sửa mốc thời gian."""
    while True:
        print("\n" + "=" * 60)
        print("          BẢNG ĐIỀU KHIỂN CẮT AUDIO 13 CÂU (INTERACTIVE)")
        print("=" * 60)
        print_preview_table(items)
        print("\nCác lệnh:")
        print("  [1-13]   : Nghe thử câu số N (ví dụ: gõ '8' để nghe câu 8)")
        print("  e <1-13> : Sửa thời gian bắt đầu/kết thúc câu số N (ví dụ: 'e 8')")
        print("  c        : Cắt và xuất toàn bộ 13 câu ngay bây giờ")
        print("  s        : Lưu cấu hình điểm cắt ra file cut_config.json")
        print("  q        : Thoát")
        
        choice = input("\nNhập lựa chọn của bạn: ").strip()
        if not choice:
            continue
        if choice.lower() == 'q':
            break
        elif choice.lower() == 'c':
            export_all_sentences(input_audio, output_dir, items, ffmpeg_bin)
            break
        elif choice.lower() == 's':
            save_config(items, "cut_config.json")
        elif choice.lower().startswith('e '):
            parts = choice.split()
            if len(parts) >= 2 and parts[1].isdigit():
                num = int(parts[1])
                if 1 <= num <= len(items):
                    item = items[num - 1]
                    print(f"\nChỉnh sửa câu {num}: \"{item['text']}\"")
                    print(f"Hiện tại: Start = {item['start']}s, End = {item['end']}s")
                    new_start = input(f"Nhập Start mới (Enter để giữ {item['start']}): ").strip()
                    new_end = input(f"Nhập End mới (Enter để giữ {item['end']}): ").strip()
                    if new_start:
                        try: item['start'] = float(new_start)
                        except ValueError: print("[!] Giá trị không hợp lệ")
                    if new_end:
                        try: item['end'] = float(new_end)
                        except ValueError: print("[!] Giá trị không hợp lệ")
                    item['duration'] = round(item['end'] - item['start'], 2)
                    print(f"[✓] Đã cập nhật câu {num}: {item['start']}s -> {item['end']}s ({item['duration']}s)")
            else:
                print("[!] Cú pháp sửa: e <số thứ tự>, ví dụ: e 8")
        elif choice.isdigit():
            num = int(choice)
            if 1 <= num <= len(items):
                item = items[num - 1]
                play_preview(input_audio, item['start'], item['end'], ffplay_bin)
            else:
                print(f"[!] Vui lòng nhập số từ 1 đến {len(items)}")
        else:
            print("[!] Lệnh không hợp lệ.")

def main():
    parser = argparse.ArgumentParser(description="Tự động cắt file audio thành 13 câu tiếng Anh riêng biệt.")
    parser.add_argument("--input", "-i", help="Đường dẫn file audio nguồn (mặc định: tự nhận diện 'sounds/4 BAI 1.mp3')")
    parser.add_argument("--output", "-o", default=os.path.join("sounds", "cut_sentences"), help="Thư mục xuất kết quả (mặc định: sounds/cut_sentences)")
    parser.add_argument("--profile", "-p", choices=["full", "quote_only"], default="full", help="Profile cắt: 'full' (gồm tên tác giả) hoặc 'quote_only' (chỉ câu)")
    parser.add_argument("--config", "-c", help="Đường dẫn file JSON cấu hình điểm cắt tùy chỉnh")
    parser.add_argument("--preview", action="store_true", help="Chỉ xem bảng điểm cắt dự kiến, không cắt")
    parser.add_argument("--play", type=int, help="Nghe thử câu thứ N (từ 1 đến 13)")
    parser.add_argument("--interactive", action="store_true", help="Chạy chế độ tương tác (nghe thử, sửa mốc, lưu cấu hình)")
    parser.add_argument("--save-config", help="Lưu cấu hình điểm cắt hiện tại ra file JSON chỉ định")
    parser.add_argument("--bitrate", default="192k", help="Bitrate MP3 xuất (mặc định: 192k)")

    args = parser.parse_args()

    # 1. Tìm công cụ FFmpeg
    ffmpeg_bin = find_ffmpeg_executable()
    ffplay_bin = find_ffplay_executable()

    # 2. Tìm file audio nguồn
    input_audio = detect_input_audio(args.input)
    if not input_audio or not os.path.isfile(input_audio):
        print("[!] LỖI: Không tìm thấy file audio nguồn! Vui lòng chỉ định bằng --input <đường dẫn>.")
        sys.exit(1)

    print(f"[*] File audio nguồn: {input_audio}")
    print(f"[*] Thư mục đầu ra  : {os.path.abspath(args.output)}")
    print(f"[*] Profile cắt     : {'Đầy đủ (câu + tác giả)' if args.profile == 'full' else 'Chỉ câu nói'}")

    # 3. Lấy cấu hình 13 câu
    items = get_sentence_configs(profile=args.profile, custom_config_path=args.config)

    # 4. Lưu cấu hình nếu có yêu cầu
    if args.save_config:
        save_config(items, args.save_config)
        return

    # 5. Xem trước
    if args.preview:
        print_preview_table(items)
        return

    # 6. Nghe thử 1 câu
    if args.play is not None:
        if 1 <= args.play <= len(items):
            item = items[args.play - 1]
            play_preview(input_audio, item['start'], item['end'], ffplay_bin)
        else:
            print(f"[!] Số thứ tự câu phải từ 1 đến {len(items)}")
        return

    # 7. Chế độ tương tác
    if args.interactive:
        interactive_mode(input_audio, items, args.output, ffmpeg_bin, ffplay_bin)
        return

    # 8. Mặc định: Hiển thị bảng xem trước và tự động cắt toàn bộ
    print_preview_table(items)
    success_files, report_file = export_all_sentences(input_audio, args.output, items, ffmpeg_bin, args.bitrate)

    if len(success_files) == len(items):
        print(f"\n[✓] HOÀN TẤT: Đã cắt thành công trọn vẹn đủ {len(items)}/13 file MP3!")
        print(f"[✓] Vị trí lưu: {os.path.abspath(args.output)}")
        print(f"[✓] Xem báo cáo tại: {report_file}")
    else:
        print(f"\n[!] CẢNH BÁO: Chỉ tạo thành công {len(success_files)}/{len(items)} file. Vui lòng kiểm tra báo cáo.")

if __name__ == "__main__":
    main()
