#!/bin/bash
# ===================================================
# 🚀 Viriyah Online Learning - Auto Approve Bot (macOS)
# Double-clickable launcher for macOS
# ===================================================

# Move to script directory
cd "$(dirname "$0")"

echo "==================================================="
echo "    🚀 Viriyah Online Learning - Auto Approve Bot"
echo "==================================================="
echo ""

# 1. Check Python 3
if ! command -v python3 &> /dev/null; then
    echo "❌ [ERROR] ไม่พบ Python 3 ในเครื่อง Mac ของคุณ"
    echo "💡 คำแนะนำ: กรุณาติดตั้ง Python 3 โดยพิมพ์ 'brew install python' หรือดาวน์โหลดจาก https://www.python.org"
    echo ""
    read -p "กด Enter เพื่อปิด..."
    exit 1
fi

# 2. Setup macOS Virtual Environment if not exists
if [ ! -f ".venv_mac/bin/python" ]; then
    echo "⚙️ [1/3] กำลังสร้าง Virtual Environment สำหรับ macOS (.venv_mac)..."
    python3 -m venv .venv_mac
    if [ $? -ne 0 ]; then
        echo "❌ [ERROR] ไม่สามารถสร้าง Virtual Environment ได้"
        read -p "กด Enter เพื่อปิด..."
        exit 1
    fi
fi

# 3. Install dependencies & Chromium
echo "📦 [2/3] กำลังตรวจสอบและติดตั้ง Dependencies..."
.venv_mac/bin/pip install --upgrade pip --quiet
.venv_mac/bin/pip install -r requirements.txt --quiet
.venv_mac/bin/python -m playwright install chromium

# 4. Launch GUI
echo ""
echo "🚀 [3/3] กำลังเปิดโปรแกรม Auto Approve..."
echo "==================================================="
.venv_mac/bin/python gui.py

# Keep window open if error occurs
if [ $? -ne 0 ]; then
    echo ""
    echo "⚠️ โปรแกรมปิดตัวลงเนื่องจากเกิดข้อผิดพลาด"
    read -p "กด Enter เพื่อปิด..."
fi
