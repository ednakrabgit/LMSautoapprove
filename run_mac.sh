#!/bin/bash
# ===================================================
# 🚀 Viriyah Online Learning - Auto Approve Bot (macOS / Linux)
# Terminal launcher script
# ===================================================

cd "$(dirname "$0")"

if ! command -v python3 &> /dev/null; then
    echo "❌ [ERROR] ไม่พบ Python 3 ในเครื่อง"
    echo "💡 กรุณาติดตั้ง Python 3 ก่อนใช้งาน (เช่น brew install python)"
    exit 1
fi

if [ ! -f ".venv_mac/bin/python" ]; then
    echo "⚙️ [1/3] กำลังสร้าง Virtual Environment (.venv_mac)..."
    python3 -m venv .venv_mac
fi

echo "📦 [2/3] กำลังตรวจสอบและติดตั้ง Dependencies..."
.venv_mac/bin/pip install --upgrade pip --quiet
.venv_mac/bin/pip install -r requirements.txt --quiet
.venv_mac/bin/python -m playwright install chromium

echo "🚀 [3/3] กำลังเปิดโปรแกรม Auto Approve..."
.venv_mac/bin/python gui.py
