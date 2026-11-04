"""
Modern GUI for Viriyah Auto Approve Bot
Built with CustomTkinter / Tkinter for desktop use.
Supports multiple workflow modes:
- Flow 1: "ผ่านการตรวจสอบ" (Approve items that passed verification)
- Flow 2: "รออนุมัติ" (Check ID verification -> Pass verification -> Approve)
"""

import os
import sys
from pathlib import Path

# Configure Playwright to use portable local ms-playwright directory if present
BASE_DIR = Path(__file__).resolve().parent
LOCAL_BROWSERS_DIR = BASE_DIR / "ms-playwright"
if LOCAL_BROWSERS_DIR.exists():
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(LOCAL_BROWSERS_DIR)

LOCAL_TCL = BASE_DIR / "python_runtime" / "tcl"
if LOCAL_TCL.exists():
    for tcl_ver in ["tcl8.6", "tcl8.7"]:
        if (LOCAL_TCL / tcl_ver).exists():
            os.environ.setdefault("TCL_LIBRARY", str(LOCAL_TCL / tcl_ver))
            break
    for tk_ver in ["tk8.6", "tk8.7"]:
        if (LOCAL_TCL / tk_ver).exists():
            os.environ.setdefault("TK_LIBRARY", str(LOCAL_TCL / tk_ver))
            break

import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
import queue

try:
    import customtkinter as ctk
    HAS_CTK = True
except ImportError:
    HAS_CTK = False

from auto_approve import AutoApproveBot, TARGET_URL


FLOW_DESC_1 = "📋 Flow 1 [ผ่านการตรวจสอบ]: เปิดแท็บใหม่ -> ถ้ามี 'ตรวจสอบใบประกาศนียบัตร' ให้ปิดทันที -> ถ้าไม่มีให้กด 'อนุมัติ' -> ยืนยัน -> รอขึ้น 'ตรวจสอบใบประกาศนียบัตร' -> ปิดแท็บ"
FLOW_DESC_2 = "📋 Flow 2 [รออนุมัติ / รออนุมัติ (ครั้งที่ 2)]: เปิดแท็บใหม่ -> ตรวจสอบ 'ผลการตรวจสอบ' (ต้องพบครบ 3 ข้อความ) -> กด 'ผ่านการตรวจสอบ' -> ยืนยัน -> กด 'อนุมัติ' -> ยืนยัน -> รอขึ้น 'ตรวจสอบใบประกาศนียบัตร' -> ปิดแท็บ"


class AutoApproveApp:
    def __init__(self):
        if HAS_CTK:
            ctk.set_appearance_mode("System")
            ctk.set_default_color_theme("blue")
            self.root = ctk.CTk()
        else:
            self.root = tk.Tk()

        self.root.title("ระบบอนุมัติการอบรมอัตโนมัติ (Viriyah Auto Approve)")
        self.root.geometry("900x720")
        self.root.minsize(800, 620)

        self.bot = None
        self.bot_thread = None
        self.log_queue = queue.Queue()

        self._build_ui()
        self._check_log_queue()

    def _build_ui(self):
        # Header / Title Bar
        if HAS_CTK:
            header_frame = ctk.CTkFrame(self.root, corner_radius=10)
            header_frame.pack(fill="x", padx=16, pady=(14, 6))

            title_lbl = ctk.CTkLabel(
                header_frame,
                text="⚡ Viriyah Online Learning - Auto Approve",
                font=ctk.CTkFont(family="Sarabun", size=20, weight="bold")
            )
            title_lbl.pack(anchor="w", padx=16, pady=(10, 2))

            self.subtitle_lbl = ctk.CTkLabel(
                header_frame,
                text=FLOW_DESC_1,
                font=ctk.CTkFont(family="Sarabun", size=12),
                text_color="gray75",
                wraplength=840,
                justify="left"
            )
            self.subtitle_lbl.pack(anchor="w", padx=16, pady=(0, 10))

            # Settings Frame
            settings_frame = ctk.CTkFrame(self.root, corner_radius=10)
            settings_frame.pack(fill="x", padx=16, pady=6)

            # Row 1: Flow Selection
            row_flow = ctk.CTkFrame(settings_frame, fg_color="transparent")
            row_flow.pack(fill="x", padx=16, pady=(10, 6))

            lbl_flow = ctk.CTkLabel(
                row_flow, 
                text="🎯 เลือก Flow การทำงาน:", 
                font=ctk.CTkFont(family="Sarabun", size=13, weight="bold")
            )
            lbl_flow.pack(side="left", padx=(0, 10))

            self.flow_options = [
                "1. ผ่านการตรวจสอบ (อนุมัติรายการที่ผ่านตรวจแล้ว)",
                "2. รออนุมัติ / รออนุมัติ (ครั้งที่ 2) (ตรวจผลตรวจบัตร -> ผ่านการตรวจสอบ -> อนุมัติ)"
            ]
            self.cbo_flow = ctk.CTkOptionMenu(
                row_flow,
                values=self.flow_options,
                command=self._on_flow_changed,
                font=ctk.CTkFont(family="Sarabun", size=13),
                width=450,
                height=32
            )
            self.cbo_flow.set(self.flow_options[0])
            self.cbo_flow.pack(side="left")

            # Row 2: Parameters
            row_params = ctk.CTkFrame(settings_frame, fg_color="transparent")
            row_params.pack(fill="x", padx=16, pady=(4, 10))

            # Remark Text
            lbl_remark = ctk.CTkLabel(row_params, text="ข้อความหมายเหตุ:", font=ctk.CTkFont(family="Sarabun", size=13))
            lbl_remark.pack(side="left", padx=(0, 6))
            self.txt_remark = ctk.CTkEntry(row_params, width=130)
            self.txt_remark.insert(0, "อนุมัติ")
            self.txt_remark.pack(side="left", padx=(0, 16))

            # Max Items
            lbl_max = ctk.CTkLabel(row_params, text="จำนวนที่ต้องการทำ (0 = ทั้งหมด):", font=ctk.CTkFont(family="Sarabun", size=13))
            lbl_max.pack(side="left", padx=(0, 6))
            self.txt_max = ctk.CTkEntry(row_params, width=70)
            self.txt_max.insert(0, "0")
            self.txt_max.pack(side="left", padx=(0, 16))

            # Delay
            lbl_delay = ctk.CTkLabel(row_params, text="หน่วงเวลา (วินาที):", font=ctk.CTkFont(family="Sarabun", size=13))
            lbl_delay.pack(side="left", padx=(0, 6))
            self.txt_delay = ctk.CTkEntry(row_params, width=65)
            self.txt_delay.insert(0, "1.5")
            self.txt_delay.pack(side="left")

            # Control Buttons Frame
            controls_frame = ctk.CTkFrame(self.root, corner_radius=10)
            controls_frame.pack(fill="x", padx=16, pady=6)

            btn_row = ctk.CTkFrame(controls_frame, fg_color="transparent")
            btn_row.pack(fill="x", padx=16, pady=10)

            self.btn_start = ctk.CTkButton(
                btn_row,
                text="▶️ เริ่มทำงาน (Start)",
                command=self._start_bot,
                font=ctk.CTkFont(family="Sarabun", size=14, weight="bold"),
                fg_color="#1f6aa5",
                hover_color="#144f7d",
                height=40,
                width=160
            )
            self.btn_start.pack(side="left", padx=(0, 10))

            self.btn_pause = ctk.CTkButton(
                btn_row,
                text="⏸️ หยุดชั่วคราว",
                command=self._pause_bot,
                font=ctk.CTkFont(family="Sarabun", size=13),
                state="disabled",
                height=40,
                width=130
            )
            self.btn_pause.pack(side="left", padx=(0, 10))

            self.btn_stop = ctk.CTkButton(
                btn_row,
                text="⏹️ ยกเลิก / หยุด",
                command=self._stop_bot,
                font=ctk.CTkFont(family="Sarabun", size=13),
                state="disabled",
                fg_color="#c0392b",
                hover_color="#962d22",
                height=40,
                width=130
            )
            self.btn_stop.pack(side="left", padx=(0, 10))

            # Status Label
            self.lbl_status = ctk.CTkLabel(
                btn_row,
                text="สถานะ: พร้อมทำงาน",
                font=ctk.CTkFont(family="Sarabun", size=13, weight="bold"),
                text_color="#2ecc71"
            )
            self.lbl_status.pack(side="right", padx=10)

            # Log Section
            log_frame = ctk.CTkFrame(self.root, corner_radius=10)
            log_frame.pack(fill="both", expand=True, padx=16, pady=(6, 14))

            log_header = ctk.CTkFrame(log_frame, fg_color="transparent")
            log_header.pack(fill="x", padx=16, pady=(8, 4))

            log_title = ctk.CTkLabel(
                log_header,
                text="📜 บันทึกการทำงาน (Live Log):",
                font=ctk.CTkFont(family="Sarabun", size=14, weight="bold")
            )
            log_title.pack(side="left")

            self.lbl_count = ctk.CTkLabel(
                log_header,
                text="ดำเนินการสำเร็จ: 0 รายการ",
                font=ctk.CTkFont(family="Sarabun", size=13, weight="bold"),
                text_color="#3498db"
            )
            self.lbl_count.pack(side="right")

            self.txt_log = ctk.CTkTextbox(
                log_frame,
                font=ctk.CTkFont(family="Consolas", size=12),
                wrap="word"
            )
            self.txt_log.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        else:
            # Tkinter Fallback UI
            frame = ttk.Frame(self.root, padding=16)
            frame.pack(fill="both", expand=True)

            ttk.Label(frame, text="Viriyah Online Learning - Auto Approve", font=("Arial", 16, "bold")).pack(anchor="w", pady=(0, 6))
            self.subtitle_lbl = ttk.Label(frame, text=FLOW_DESC_1, wraplength=760)
            self.subtitle_lbl.pack(anchor="w", pady=(0, 10))

            flow_frame = ttk.Frame(frame)
            flow_frame.pack(fill="x", pady=5)
            ttk.Label(flow_frame, text="เลือก Flow:").pack(side="left", padx=5)
            self.cbo_flow = ttk.Combobox(
                flow_frame, 
                values=["ผ่านการตรวจสอบ", "รออนุมัติ"],
                state="readonly",
                width=30
            )
            self.cbo_flow.set("ผ่านการตรวจสอบ")
            self.cbo_flow.bind("<<ComboboxSelected>>", lambda e: self._on_flow_changed(self.cbo_flow.get()))
            self.cbo_flow.pack(side="left", padx=5)

            ctrl_frame = ttk.Frame(frame)
            ctrl_frame.pack(fill="x", pady=10)

            self.btn_start = ttk.Button(ctrl_frame, text="เริ่มทำงาน (Start)", command=self._start_bot)
            self.btn_start.pack(side="left", padx=5)
            self.btn_pause = ttk.Button(ctrl_frame, text="หยุดชั่วคราว", command=self._pause_bot, state="disabled")
            self.btn_pause.pack(side="left", padx=5)
            self.btn_stop = ttk.Button(ctrl_frame, text="หยุด", command=self._stop_bot, state="disabled")
            self.btn_stop.pack(side="left", padx=5)

            self.lbl_status = ttk.Label(ctrl_frame, text="สถานะ: พร้อมทำงาน")
            self.lbl_status.pack(side="right", padx=5)

            self.txt_log = tk.Text(frame, wrap="word", height=20)
            self.txt_log.pack(fill="both", expand=True, pady=10)

    def _on_flow_changed(self, choice: str):
        """Updates UI description and default remarks when flow option changes."""
        if "รออนุมัติ" in choice:
            desc = FLOW_DESC_2
            if HAS_CTK:
                self.subtitle_lbl.configure(text=desc)
        else:
            desc = FLOW_DESC_1
            if HAS_CTK:
                self.subtitle_lbl.configure(text=desc)

    def _append_log(self, msg: str):
        self.log_queue.put(("log", msg))

    def _update_progress(self, count: int, total: int):
        self.log_queue.put(("progress", (count, total)))

    def _update_status(self, status: str):
        self.log_queue.put(("status", status))

    def _check_log_queue(self):
        try:
            while not self.log_queue.empty():
                msg_type, data = self.log_queue.get_nowait()
                if msg_type == "log":
                    self.txt_log.insert("end", data + "\n")
                    self.txt_log.see("end")
                elif msg_type == "status":
                    if HAS_CTK:
                        self.lbl_status.configure(text=f"สถานะ: {data}")
                    else:
                        self.lbl_status.config(text=f"สถานะ: {data}")
                elif msg_type == "progress":
                    count, total = data
                    total_str = f" / {total}" if total > 0 else ""
                    if HAS_CTK:
                        self.lbl_count.configure(text=f"ดำเนินการสำเร็จ: {count}{total_str} รายการ")
        except Exception:
            pass
        finally:
            self.root.after(100, self._check_log_queue)

    def _start_bot(self):
        # Determine selected flow
        if HAS_CTK:
            flow_choice = self.cbo_flow.get()
            flow_type = "รออนุมัติ" if "รออนุมัติ" in flow_choice else "ผ่านการตรวจสอบ"
            remark = self.txt_remark.get().strip()
            try:
                max_items = int(self.txt_max.get().strip())
            except ValueError:
                max_items = 0
            try:
                delay = float(self.txt_delay.get().strip())
            except ValueError:
                delay = 1.5
        else:
            flow_type = "รออนุมัติ" if "รออนุมัติ" in self.cbo_flow.get() else "ผ่านการตรวจสอบ"
            remark = "อนุมัติ"
            max_items = 0
            delay = 1.5

        self.bot = AutoApproveBot(
            log_callback=self._append_log,
            progress_callback=self._update_progress,
            status_callback=self._update_status,
            flow_type=flow_type,
            remark_text=remark if remark else "อนุมัติ",
            delay_seconds=delay,
            max_items=max_items,
            headless=False
        )

        if HAS_CTK:
            self.btn_start.configure(state="disabled")
            self.cbo_flow.configure(state="disabled")
            self.btn_pause.configure(state="normal", text="⏸️ หยุดชั่วคราว")
            self.btn_stop.configure(state="normal")
        else:
            self.btn_start.config(state="disabled")
            self.btn_pause.config(state="normal")
            self.btn_stop.config(state="normal")

        def run_thread():
            try:
                self.bot.run()
            finally:
                self.root.after(0, self._on_bot_finished)

        self.bot_thread = threading.Thread(target=run_thread, daemon=True)
        self.bot_thread.start()

    def _pause_bot(self):
        if not self.bot:
            return
        if self.bot.is_paused:
            self.bot.resume()
            if HAS_CTK:
                self.btn_pause.configure(text="⏸️ หยุดชั่วคราว")
        else:
            self.bot.pause()
            if HAS_CTK:
                self.btn_pause.configure(text="▶️ ทำงานต่อ")

    def _stop_bot(self):
        if self.bot:
            self.bot.stop()
        self._on_bot_finished()

    def _on_bot_finished(self):
        if HAS_CTK:
            self.btn_start.configure(state="normal")
            self.cbo_flow.configure(state="normal")
            self.btn_pause.configure(state="disabled", text="⏸️ หยุดชั่วคราว")
            self.btn_stop.configure(state="disabled")
            self.lbl_status.configure(text="สถานะ: หยุดการทำงาน / พร้อมเริ่มใหม่")
        else:
            self.btn_start.config(state="normal")
            self.btn_pause.config(state="disabled")
            self.btn_stop.config(state="disabled")
            self.lbl_status.config(text="สถานะ: พร้อมทำงาน")

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = AutoApproveApp()
    app.run()
