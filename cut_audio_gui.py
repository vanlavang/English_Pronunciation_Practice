#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Giao diện đồ họa (GUI) tự động cắt audio thành các câu tiếng Anh riêng biệt.
Hỗ trợ Bài 1 (13 câu) & Bài 2 (12 câu), sử dụng Tkinter chuẩn kết hợp FFmpeg.

Tác giả: Antigravity AI Pair Programmer
"""

import os
import sys
import json
import threading
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

try:
    from cut_audio_sentences import (
        LESSONS_DATA,
        find_ffmpeg_executable,
        find_ffplay_executable,
        detect_audio_for_lesson,
        detect_input_audio,
        guess_lesson_from_filename,
        get_sentence_configs,
        export_all_sentences
    )
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from cut_audio_sentences import (
        LESSONS_DATA,
        find_ffmpeg_executable,
        find_ffplay_executable,
        detect_audio_for_lesson,
        detect_input_audio,
        guess_lesson_from_filename,
        get_sentence_configs,
        export_all_sentences
    )

class AudioCutterGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("✂️ Cắt Audio Theo Câu Tiếng Anh - Master Pronunciation")
        self.geometry("980x720")
        self.minsize(860, 600)
        self.configure(bg="#f1f5f9")

        self.ffmpeg_bin = find_ffmpeg_executable()
        self.ffplay_bin = find_ffplay_executable()
        self.playing_proc = None

        self.lesson_var = tk.IntVar(value=1)
        self.profile_var = tk.StringVar(value="full")
        self.input_audio_var = tk.StringVar()
        self.output_dir_var = tk.StringVar(value=os.path.abspath(os.path.join("sounds", "cut_sentences")))

        detected = detect_input_audio()
        if detected:
            self.input_audio_var.set(detected)
            self.lesson_var.set(guess_lesson_from_filename(detected))

        self.items = get_sentence_configs(lesson_num=self.lesson_var.get(), profile=self.profile_var.get())

        self.create_widgets()
        self.update_table()

    def create_widgets(self):
        # Header
        header_frame = tk.Frame(self, bg="#2563eb", padx=16, pady=12)
        header_frame.pack(fill=tk.X)
        
        lbl_title = tk.Label(
            header_frame,
            text="🎧 CẮT FILE AUDIO THÀNH TỪNG CÂU TIẾNG ANH (FFMPEG AUTO CUTTER)",
            font=("Segoe UI", 14, "bold"),
            fg="white",
            bg="#2563eb"
        )
        lbl_title.pack(anchor="w")

        lbl_sub = tk.Label(
            header_frame,
            text="Hỗ trợ Bài 1 (13 câu) & Bài 2 (12 câu) | Tự động phân tích khoảng lặng | Đệm padding chống mất âm",
            font=("Segoe UI", 9),
            fg="#bfdbfe",
            bg="#2563eb"
        )
        lbl_sub.pack(anchor="w")

        # Main container
        main_frame = tk.Frame(self, bg="#f1f5f9", padx=14, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 1. File I/O Settings
        io_frame = tk.LabelFrame(main_frame, text=" 📂 Cấu hình File & Bài học ", font=("Segoe UI", 10, "bold"), bg="#ffffff", padx=12, pady=8)
        io_frame.pack(fill=tk.X, pady=(0, 10))

        # Chọn bài học
        tk.Label(io_frame, text="Chọn bài học:", font=("Segoe UI", 9, "bold"), bg="#ffffff").grid(row=0, column=0, sticky="w", pady=4)
        lesson_selector_frame = tk.Frame(io_frame, bg="#ffffff")
        lesson_selector_frame.grid(row=0, column=1, sticky="w", padx=8, pady=4)

        for l_num, l_cfg in LESSONS_DATA.items():
            rb_l = tk.Radiobutton(
                lesson_selector_frame,
                text=l_cfg["title"],
                variable=self.lesson_var,
                value=l_num,
                command=self.on_lesson_change,
                bg="#ffffff",
                font=("Segoe UI", 9, "bold" if l_num == 1 else "normal")
            )
            rb_l.pack(side=tk.LEFT, padx=8)

        # Input audio
        tk.Label(io_frame, text="File audio nguồn:", font=("Segoe UI", 9, "bold"), bg="#ffffff").grid(row=1, column=0, sticky="w", pady=4)
        entry_input = tk.Entry(io_frame, textvariable=self.input_audio_var, font=("Segoe UI", 9), width=70)
        entry_input.grid(row=1, column=1, sticky="ew", padx=8, pady=4)
        btn_browse_in = tk.Button(io_frame, text="Chọn file...", command=self.browse_input_audio, bg="#e2e8f0", relief="groove")
        btn_browse_in.grid(row=1, column=2, pady=4)

        # Output dir
        tk.Label(io_frame, text="Thư mục xuất file:", font=("Segoe UI", 9, "bold"), bg="#ffffff").grid(row=2, column=0, sticky="w", pady=4)
        entry_output = tk.Entry(io_frame, textvariable=self.output_dir_var, font=("Segoe UI", 9), width=70)
        entry_output.grid(row=2, column=1, sticky="ew", padx=8, pady=4)
        btn_browse_out = tk.Button(io_frame, text="Chọn thư mục...", command=self.browse_output_dir, bg="#e2e8f0", relief="groove")
        btn_browse_out.grid(row=2, column=2, pady=4)

        # Profile selection
        profile_frame = tk.Frame(io_frame, bg="#ffffff")
        profile_frame.grid(row=3, column=0, columnspan=3, sticky="w", pady=(6, 2))
        tk.Label(profile_frame, text="Chế độ cắt:", font=("Segoe UI", 9, "bold"), bg="#ffffff").pack(side=tk.LEFT, padx=(0, 10))
        
        rb1 = tk.Radiobutton(profile_frame, text="Đầy đủ (câu + tên tác giả nếu có)", variable=self.profile_var, value="full", command=self.on_profile_change, bg="#ffffff")
        rb1.pack(side=tk.LEFT, padx=6)
        rb2 = tk.Radiobutton(profile_frame, text="Chỉ câu nói (bỏ qua tên tác giả đọc ở cuối)", variable=self.profile_var, value="quote_only", command=self.on_profile_change, bg="#ffffff")
        rb2.pack(side=tk.LEFT, padx=6)

        io_frame.columnconfigure(1, weight=1)

        # 2. Table of sentences
        table_frame = tk.LabelFrame(main_frame, text=" 📋 Danh sách các câu & Điểm cắt dự kiến ", font=("Segoe UI", 10, "bold"), bg="#ffffff", padx=10, pady=8)
        table_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        cols = ("stt", "filename", "start", "end", "duration", "text")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=12)
        self.tree.heading("stt", text="STT")
        self.tree.heading("filename", text="Tên file đích")
        self.tree.heading("start", text="Bắt đầu (s)")
        self.tree.heading("end", text="Kết thúc (s)")
        self.tree.heading("duration", text="Thời lượng (s)")
        self.tree.heading("text", text="Nội dung câu tiếng Anh đối chiếu")

        self.tree.column("stt", width=45, anchor="center")
        self.tree.column("filename", width=120, anchor="w")
        self.tree.column("start", width=80, anchor="center")
        self.tree.column("end", width=80, anchor="center")
        self.tree.column("duration", width=90, anchor="center")
        self.tree.column("text", width=500, anchor="w")

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<Double-1>", self.on_double_click_item)

        # 3. Control Buttons Bar
        bar_frame = tk.Frame(main_frame, bg="#f1f5f9")
        bar_frame.pack(fill=tk.X, pady=(0, 6))

        btn_play = tk.Button(bar_frame, text="🔊 Nghe thử câu chọn", font=("Segoe UI", 9, "bold"), bg="#0284c7", fg="white", padx=10, pady=5, relief="flat", command=self.play_selected)
        btn_play.pack(side=tk.LEFT, padx=(0, 6))

        btn_stop = tk.Button(bar_frame, text="⏹ Dừng", font=("Segoe UI", 9), bg="#e2e8f0", padx=8, pady=5, relief="flat", command=self.stop_audio)
        btn_stop.pack(side=tk.LEFT, padx=(0, 6))

        btn_edit = tk.Button(bar_frame, text="✏️ Sửa thời gian", font=("Segoe UI", 9), bg="#f8fafc", relief="groove", padx=8, pady=5, command=self.edit_selected)
        btn_edit.pack(side=tk.LEFT, padx=(0, 6))

        btn_reset = tk.Button(bar_frame, text="🔄 Đặt lại", font=("Segoe UI", 9), bg="#f8fafc", relief="groove", padx=8, pady=5, command=self.reset_timings)
        btn_reset.pack(side=tk.LEFT, padx=(0, 6))

        btn_save = tk.Button(bar_frame, text="💾 Lưu JSON", font=("Segoe UI", 9), bg="#f8fafc", relief="groove", padx=8, pady=5, command=self.export_config_json)
        btn_save.pack(side=tk.LEFT, padx=(0, 6))

        btn_load = tk.Button(bar_frame, text="📂 Nạp JSON", font=("Segoe UI", 9), bg="#f8fafc", relief="groove", padx=8, pady=5, command=self.import_config_json)
        btn_load.pack(side=tk.LEFT, padx=(0, 6))

        # Big Cut Action Button
        btn_cut_all = tk.Button(
            bar_frame,
            text="✂️ TỰ ĐỘNG CẮT CÁC CÂU NGAY",
            font=("Segoe UI", 10, "bold"),
            bg="#16a34a",
            fg="white",
            padx=14,
            pady=5,
            relief="flat",
            cursor="hand2",
            command=self.start_cutting_thread
        )
        btn_cut_all.pack(side=tk.RIGHT)

        btn_open_folder = tk.Button(
            bar_frame,
            text="📁 Mở thư mục kết quả",
            font=("Segoe UI", 9),
            bg="#f8fafc",
            relief="groove",
            padx=8,
            pady=5,
            command=self.open_output_folder
        )
        btn_open_folder.pack(side=tk.RIGHT, padx=6)

        # 4. Status Bar
        status_frame = tk.Frame(self, bg="#e2e8f0", padx=12, pady=6)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.progress_bar = ttk.Progressbar(status_frame, orient="horizontal", mode="determinate")
        self.progress_bar.pack(side=tk.RIGHT, padx=8, ipadx=50)

        self.lbl_status = tk.Label(status_frame, text="Sẵn sàng.", font=("Segoe UI", 9), bg="#e2e8f0", fg="#334155")
        self.lbl_status.pack(side=tk.LEFT)

    def on_lesson_change(self):
        l_num = self.lesson_var.get()
        auto_file = detect_audio_for_lesson(l_num)
        if auto_file:
            self.input_audio_var.set(auto_file)
        self.items = get_sentence_configs(lesson_num=l_num, profile=self.profile_var.get())
        self.update_table()
        self.lbl_status.config(text=f"Đã chuyển sang Bài {l_num} ({len(self.items)} câu).")

    def browse_input_audio(self):
        f = filedialog.askopenfilename(
            title="Chọn file audio nguồn",
            filetypes=[("Audio Files", "*.mp3 *.wav *.m4a *.aac *.flac"), ("All Files", "*.*")]
        )
        if f:
            self.input_audio_var.set(os.path.abspath(f))
            guessed = guess_lesson_from_filename(f)
            self.lesson_var.set(guessed)
            self.items = get_sentence_configs(lesson_num=guessed, profile=self.profile_var.get())
            self.update_table()
            self.lbl_status.config(text=f"Đã chọn file: {os.path.basename(f)} (Nhận diện Bài {guessed})")

    def browse_output_dir(self):
        d = filedialog.askdirectory(title="Chọn thư mục xuất file")
        if d:
            self.output_dir_var.set(os.path.abspath(d))

    def on_profile_change(self):
        self.items = get_sentence_configs(lesson_num=self.lesson_var.get(), profile=self.profile_var.get())
        self.update_table()

    def reset_timings(self):
        self.on_profile_change()

    def update_table(self):
        self.tree.delete(*self.tree.get_children())
        for it in self.items:
            note = f" (+ {it['author']})" if it.get("author") else ""
            self.tree.insert(
                "",
                tk.END,
                values=(
                    it["index"],
                    it["filename"],
                    f"{it['start']:.2f}",
                    f"{it['end']:.2f}",
                    f"{it['duration']:.2f}",
                    it["text"] + note
                )
            )

    def get_selected_item_index(self) -> Optional[int]:
        sel = self.tree.selection()
        if not sel:
            return None
        item_vals = self.tree.item(sel[0], "values")
        if item_vals:
            return int(item_vals[0]) - 1
        return None

    def play_selected(self):
        idx = self.get_selected_item_index()
        if idx is None:
            messagebox.showinfo("Thông báo", "Vui lòng chọn 1 câu trong bảng để nghe thử!")
            return

        audio_file = self.input_audio_var.get()
        if not os.path.isfile(audio_file):
            messagebox.showerror("Lỗi", "Không tìm thấy file audio nguồn!")
            return

        item = self.items[idx]
        self.stop_audio()
        duration = item['end'] - item['start']
        self.lbl_status.config(text=f"🔊 Đang phát câu {item['index']}: {item['start']:.2f}s -> {item['end']:.2f}s...")

        def _play():
            cmd = [
                self.ffplay_bin,
                "-ss", str(item['start']),
                "-t", str(duration),
                "-autoexit",
                "-nodisp",
                "-loglevel", "quiet",
                audio_file
            ]
            self.playing_proc = subprocess.Popen(cmd)
            self.playing_proc.wait()
            self.lbl_status.config(text="Đã phát xong.")

        threading.Thread(target=_play, daemon=True).start()

    def stop_audio(self):
        if self.playing_proc and self.playing_proc.poll() is None:
            try: self.playing_proc.terminate()
            except Exception: pass
            self.playing_proc = None
            self.lbl_status.config(text="Đã dừng phát.")

    def on_double_click_item(self, event):
        self.edit_selected()

    def edit_selected(self):
        idx = self.get_selected_item_index()
        if idx is None:
            messagebox.showinfo("Thông báo", "Vui lòng chọn 1 câu để chỉnh sửa thời gian!")
            return

        item = self.items[idx]
        dlg = tk.Toplevel(self)
        dlg.title(f"Chỉnh sửa câu {item['index']}")
        dlg.geometry("450x260")
        dlg.resizable(False, False)
        dlg.transient(self)
        dlg.grab_set()

        tk.Label(dlg, text=f"Câu {item['index']}: {item['filename']}", font=("Segoe UI", 10, "bold"), fg="#2563eb").pack(pady=(12, 4))
        tk.Label(dlg, text=f"\"{item['text']}\"", font=("Segoe UI", 9, "italic"), wraplength=400).pack(pady=(0, 10))

        f_inputs = tk.Frame(dlg)
        f_inputs.pack(pady=5)

        tk.Label(f_inputs, text="Bắt đầu (s):", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, padx=6, pady=4, sticky="e")
        ent_start = tk.Entry(f_inputs, font=("Segoe UI", 9), width=12)
        ent_start.insert(0, str(item['start']))
        ent_start.grid(row=0, column=1, padx=6, pady=4)

        tk.Label(f_inputs, text="Kết thúc (s):", font=("Segoe UI", 9, "bold")).grid(row=1, column=0, padx=6, pady=4, sticky="e")
        ent_end = tk.Entry(f_inputs, font=("Segoe UI", 9), width=12)
        ent_end.insert(0, str(item['end']))
        ent_end.grid(row=1, column=1, padx=6, pady=4)

        def _save_changes():
            try:
                s = float(ent_start.get().strip())
                e = float(ent_end.get().strip())
                if s < 0 or e <= s:
                    messagebox.showerror("Lỗi", "Thời gian bắt đầu phải >= 0 và kết thúc phải lớn hơn bắt đầu!")
                    return
                item['start'] = round(s, 2)
                item['end'] = round(e, 2)
                item['duration'] = round(e - s, 2)
                self.update_table()
                dlg.destroy()
                self.lbl_status.config(text=f"Đã cập nhật câu {item['index']}: {item['start']}s -> {item['end']}s")
            except ValueError:
                messagebox.showerror("Lỗi", "Vui lòng nhập số hợp lệ!")

        def _test_in_dialog():
            try:
                s = float(ent_start.get().strip())
                e = float(ent_end.get().strip())
                self.stop_audio()
                threading.Thread(
                    target=lambda: subprocess.run([
                        self.ffplay_bin, "-ss", str(s), "-t", str(e - s), "-autoexit", "-nodisp", "-loglevel", "quiet", self.input_audio_var.get()
                    ]),
                    daemon=True
                ).start()
            except Exception as ex:
                messagebox.showerror("Lỗi", str(ex))

        f_btns = tk.Frame(dlg)
        f_btns.pack(pady=15)
        tk.Button(f_btns, text="🔊 Nghe thử mốc mới", command=_test_in_dialog, bg="#e2e8f0").pack(side=tk.LEFT, padx=6)
        tk.Button(f_btns, text="💾 Lưu thay đổi", command=_save_changes, bg="#16a34a", fg="white", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=6)
        tk.Button(f_btns, text="Hủy", command=dlg.destroy, bg="#f1f5f9").pack(side=tk.LEFT, padx=6)

    def export_config_json(self):
        f = filedialog.asksaveasfilename(
            title="Lưu cấu hình điểm cắt ra JSON",
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json")]
        )
        if f:
            with open(f, "w", encoding="utf-8") as fp:
                json.dump(self.items, fp, ensure_ascii=False, indent=2)
            messagebox.showinfo("Thành công", f"Đã lưu cấu hình vào:\n{f}")

    def import_config_json(self):
        f = filedialog.askopenfilename(
            title="Chọn file cấu hình JSON",
            filetypes=[("JSON Files", "*.json")]
        )
        if f:
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    self.items = json.load(fp)
                self.update_table()
                messagebox.showinfo("Thành công", "Đã nạp cấu hình thành công!")
            except Exception as ex:
                messagebox.showerror("Lỗi", f"Không thể đọc file JSON:\n{ex}")

    def open_output_folder(self):
        d = self.output_dir_var.get()
        if not os.path.exists(d):
            os.makedirs(d, exist_ok=True)
        os.startfile(d)

    def start_cutting_thread(self):
        audio_file = self.input_audio_var.get()
        if not os.path.isfile(audio_file):
            messagebox.showerror("Lỗi", "Không tìm thấy file audio nguồn!")
            return

        output_dir = self.output_dir_var.get()
        self.progress_bar["value"] = 0
        self.progress_bar["maximum"] = len(self.items)

        def _worker():
            self.lbl_status.config(text=f"⏳ Đang cắt {len(self.items)} câu bằng FFmpeg...")
            l_num = self.lesson_var.get()
            rep_name = f"cut_report_bai{l_num}.txt" if l_num != 1 else "cut_report.txt"
            success_files, report_file = export_all_sentences(
                audio_file,
                output_dir,
                self.items,
                self.ffmpeg_bin,
                report_filename=rep_name
            )

            self.progress_bar["value"] = len(self.items)
            if len(success_files) == len(self.items):
                msg = f"🎉 XUẤT THÀNH CÔNG ĐỦ {len(self.items)} FILE!\n\nThư mục:\n{output_dir}\n\nĐã tạo báo cáo:\n{os.path.basename(report_file)}"
                self.lbl_status.config(text="✓ Đã cắt xong toàn bộ câu thành công!")
                if messagebox.askyesno("Hoàn tất", f"{msg}\n\nBạn có muốn mở thư mục kết quả ngay bây giờ không?"):
                    self.open_output_folder()
            else:
                self.lbl_status.config(text=f"[!] Cảnh báo: Chỉ xuất được {len(success_files)}/{len(self.items)} file.")
                messagebox.showwarning("Cảnh báo", f"Chỉ tạo được {len(success_files)}/{len(self.items)} file.")

        threading.Thread(target=_worker, daemon=True).start()

def main():
    app = AudioCutterGUI()
    app.mainloop()

if __name__ == "__main__":
    main()
