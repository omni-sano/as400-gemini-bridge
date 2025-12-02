#!/bin/bash
cd /home/blog/gemini
export PATH=/QOpenSys/pkgs/bin:$PATH
. .venv/bin/activate
python analyze.py "$@"

# 出力ファイルのCCSIDを1208(UTF-8)に設定
OUTPUT="$3"
setccsid 1208 "$OUTPUT"
