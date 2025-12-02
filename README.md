# AS/400 Gemini Bridge

AS/400（IBM i）のデータをVertex AI Gemini APIで分析するツール。

## 必要要件

- IBM i 7.3以降
- Python 3.9+
- pyodbc（システムパッケージ）
- Google Cloud サービスアカウント

## セットアップ

### 1. 事前準備（yum）

```bash
yum install python39 python39-pip python39-pyodbc unixODBC ibm-iaccess
```
> Pythonのバージョンは3.9以上ならお好みのバージョンに

PATHを通す：

```bash
export PATH=/QOpenSys/pkgs/bin:$PATH
```
> すでに設定されているなら不要です

### 2. プログラム配置

```bash
mkdir -p /home/blog/gemini
cd /home/blog/gemini

# ファイルを配置
# - analyze.py
# - run_analyze.sh
# - pyproject.toml
# - .env
# - vertex-ai-credentials.json
```

### 3. venv作成

```bash
cd /home/blog/gemini

# システムパッケージを継承する .venv を作成（pyodbc用）
python -m venv .venv --system-site-packages

# 有効化
. .venv/bin/activate

# インストール
pip install -e .
```

### 4. 設定

`.env` ファイルを作成：

```
GCP_PROJECT_ID=your-project-id
GCP_REGION=asia-northeast1
MODEL=gemini-2.0-flash
GOOGLE_APPLICATION_CREDENTIALS=vertex-ai-credentials.json

# ODBC接続（デフォルト: DSN=*LOCAL）
ODBC_CONNECTION=DSN=*LOCAL
```

サービスアカウントの認証情報JSONを `vertex-ai-credentials.json` として配置。

### 5. シェルスクリプトに実行権限付与

```bash
chmod +x /home/blog/gemini/run_analyze.sh
```

### 6. コマンド・CLプログラムのコンパイル

```
CRTCMD CMD(YOURLIB/ANALYZE) PGM(YOURLIB/ANALYZEC) SRCSTMF('/home/blog/gemini/ANALYZE.CMD')
CRTBNDCL PGM(YOURLIB/ANALYZEC) SRCSTMF('/home/blog/gemini/ANALYZE.CLLE')
```

## 使い方

### コマンドから実行

```
YOURLIB/ANALYZE TABLE('MYLIB/SALES') QUESTION('売上の傾向を分析して')
```

結果は `QTEMP.GEMINI` に格納されます：

```sql
SELECT * FROM QTEMP.GEMINI ORDER BY SEQ
```

### テーブル構造

```sql
QTEMP.GEMINI (
    SEQ INT,           -- 行番号
    RESULT VARCHAR(2048) CCSID 1208  -- 結果テキスト
)
```

## サンプルデータの投入

### 1. テーブル作成

```sql
CREATE OR REPLACE TABLE YOURLIB.SALES (
    SALEDATE DATE,
    ITEMCD VARCHAR(10) CCSID 1208,
    ITEMNAME VARCHAR(50) CCSID 1208,
    QTY INT,
    PRICE INT,
    AMOUNT INT,
    CUSTOMER VARCHAR(50) CCSID 1208,
    REGION VARCHAR(20) CCSID 1208,
    STAFF VARCHAR(20) CCSID 1208
);

LABEL ON COLUMN YOURLIB.SALES (
    SALEDATE IS '日付',
    ITEMCD IS '商品コード',
    ITEMNAME IS '商品名',
    QTY IS '数量',
    PRICE IS '単価',
    AMOUNT IS '金額',
    CUSTOMER IS '顧客名',
    REGION IS '地域',
    STAFF IS '担当者'
);
```

### 2. CSVを投入

CSVをIFSに配置後：

```
CPYFRMIMPF FROMSTMF('/home/blog/gemini/sample_sales.csv') TOFILE(YOURLIB/SALES) RCDDLM(*CRLF) STRDLM(*NONE) FLDDLM(',') RMVBLANK(*TRAILING) FROMRCD(2)
```

## 注意事項

- APIタイムアウト: 2分
- エラー発生時はエラーメッセージがQTEMP.GEMINIに格納されます
