#!/bin/bash
# Script untuk memastikan bot Qrem tetap menyala otomatis jika server PythonAnywhere melakukan restart harian
cd "$(dirname "$0")"
source .venv/bin/activate

if ! pgrep -f "python bot.py" > /dev/null
then
    echo "[$(date)] Bot mati, menyalakan kembali..." >> bot.log
    nohup python bot.py >> bot.log 2>&1 &
else
    echo "[$(date)] Bot sudah aktif." >> bot.log
fi
