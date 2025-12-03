#!/usr/bin/env python3
import sys
import os
import pyodbc
import csv
import io
import json
import time
import requests
import jwt
from dotenv import load_dotenv


def get_access_token(credentials_path):
    """サービスアカウントからアクセストークンを取得"""
    with open(credentials_path) as f:
        creds = json.load(f)

    now = int(time.time())
    payload = {
        'iss': creds['client_email'],
        'sub': creds['client_email'],
        'aud': 'https://oauth2.googleapis.com/token',
        'iat': now,
        'exp': now + 3600,
        'scope': 'https://www.googleapis.com/auth/cloud-platform'
    }

    signed_jwt = jwt.encode(payload, creds['private_key'], algorithm='RS256')

    resp = requests.post('https://oauth2.googleapis.com/token', data={
        'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
        'assertion': signed_jwt
    })
    resp.raise_for_status()
    return resp.json()['access_token']


def call_gemini(access_token, project_id, region, model, prompt):
    """Vertex AI Gemini REST API呼び出し"""
    url = f'https://{region}-aiplatform.googleapis.com/v1beta1/projects/{project_id}/locations/{region}/publishers/google/models/{model}:generateContent'

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    body = {
        'contents': [{
            'role': 'user',
            'parts': [{'text': prompt}]
        }]
    }

    # google-genai が使うパッケージにRustコンパイルが必要なものがあるため、直接REST APIを呼び出しています
    try:
        resp = requests.post(url, headers=headers, json=body, timeout=120)
    except requests.exceptions.Timeout:
        return "Error: APIタイムアウト（2分経過）"
    except requests.exceptions.RequestException as e:
        return f"Error: リクエスト失敗 - {e}"

    if resp.status_code != 200:
        return f"Error {resp.status_code}: {resp.text}"

    result = resp.json()

    # エラーチェック
    if 'candidates' not in result:
        return f"Error: No candidates in response: {result}"
    if len(result['candidates']) == 0:
        return f"Error: Empty candidates: {result}"
    if 'content' not in result['candidates'][0]:
        return f"Error: No content: {result['candidates'][0]}"
    if 'parts' not in result['candidates'][0]['content']:
        return f"Error: No parts: {result['candidates'][0]['content']}"

    return result['candidates'][0]['content']['parts'][0]['text']


def get_column_labels(cursor, lib, table):
    """カラムのラベルまたはテキストを取得"""
    cursor.execute(f'''
        SELECT COLUMN_NAME, COLUMN_HEADING, COLUMN_TEXT
        FROM QSYS2.SYSCOLUMNS
        WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?
        ORDER BY ORDINAL_POSITION
    ''', (lib.upper(), table.upper()))

    # CSVのカラムラベル取得
    labels = {}
    for row in cursor.fetchall():
        col_name = row[0]
        col_heading = row[1]  # COLHDG（ラベル）
        col_text = row[2]     # TEXT（表示テキスト）

        # 優先順位: TEXT > COLHDG > COLUMN_NAME
        if col_text and col_text.strip():
            labels[col_name] = col_text.strip()
        elif col_heading and col_heading.strip():
            labels[col_name] = col_heading.strip()
        else:
            labels[col_name] = col_name

    return labels


def main():
    load_dotenv()

    if len(sys.argv) < 4:
        print("Usage: analyze.py LIB/TABLE 'question' /path/to/output.txt")
        sys.exit(1)

    table_path = sys.argv[1]
    question = sys.argv[2]
    output = sys.argv[3]

    lib, table = table_path.split('/')

    # 設定
    PROJECT_ID = os.getenv('GCP_PROJECT_ID')
    REGION = os.getenv('GCP_REGION', 'asia-northeast1')
    MODEL = os.getenv('MODEL', 'gemini-2.0-flash')
    CREDENTIALS_PATH = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'vertex-ai-credentials.json')
    ODBC_CONNECTION = os.getenv('ODBC_CONNECTION', 'DSN=*LOCAL')

    # DB接続
    conn = pyodbc.connect(ODBC_CONNECTION)
    cursor = conn.cursor()

    # カラムラベル取得
    labels = get_column_labels(cursor, lib, table)

    # データ取得してCSV化
    # プロンプトに直接展開するので一応最大件数は指定しておく
    cursor.execute(f'SELECT * FROM {lib}.{table} FETCH FIRST 5000 ROWS ONLY')
    columns = [desc[0] for desc in cursor.description]

    # ラベルに変換
    header = [labels.get(col, col) for col in columns]

    rows = cursor.fetchall()

    csv_buffer = io.StringIO()
    writer = csv.writer(csv_buffer)
    writer.writerow(header)  # ラベルをヘッダーに
    for row in rows:
        writer.writerow(row)
    csv_data = csv_buffer.getvalue()

    # アクセストークン取得
    access_token = get_access_token(CREDENTIALS_PATH)

    # Gemini呼び出し
    prompt = f"""以下のCSVデータを分析してください。

質問: {question}

データ:
{csv_data}
"""
    result = call_gemini(access_token, PROJECT_ID, REGION, MODEL, prompt)

    # 出力
    with open(output, 'w', encoding='utf-8') as f:
        f.write(result)

    conn.close()


if __name__ == '__main__':
    main()
