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
> Pythonのバージョンは3.9以上ならお好みのバージョンに変更してください

PATHを通す：

```bash
export PATH=/QOpenSys/pkgs/bin:$PATH
```
> すでに設定されているなら不要です

### 2. プログラム配置

```bash
mkdir -p /home/blog/gemini
cd /home/blog/gemini
```

以下のファイルを `/home/blog/gemini/` に配置：

- `analyze.py` - メインスクリプト
- `run_analyze.sh` - シェルスクリプト
- `pyproject.toml` - Python設定
- `ANALYZE.CMD` - コマンド定義
- `ANALYZE.CLLE` - CLプログラムソース
- `.env` - 環境設定 ※ .env.exampleを参考に作成してください
- `vertex-ai-credentials.json` - GCP認証情報
- `create_gemini.sql` - GEMINIテーブル作成SQL ※API-BRIDGE用のダミーテーブル
- `create_sales.sql` - SALESテーブル作成SQL
- `insert_sales.sql` - サンプルデータ投入SQL
> vertex-ai-credentials.jsonは別途用意してください

### 3. venv作成

```bash
cd /home/blog/gemini

# Pythonの実行環境作成
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
> .env.exampleを参考にしてください

サービスアカウントの認証情報JSONを `vertex-ai-credentials.json` として配置してください。

### 5. シェルスクリプトに実行権限付与

```bash
chmod +x /home/blog/gemini/run_analyze.sh
```

### 6. コマンド・CLプログラムのコンパイル

```
CRTCMD CMD(YOURLIB/ANALYZE) PGM(YOURLIB/ANALYZEC) SRCSTMF('/home/blog/gemini/ANALYZE.CMD')
CRTBNDCL PGM(YOURLIB/ANALYZEC) SRCSTMF('/home/blog/gemini/ANALYZE.CLLE')
```
> 実際に外部から起動するのはANALYZEになります。実際の処理はANALYZECが行います

## 使い方

### コマンドから実行

5250から直接コマンドを実行する場合は、`ANALYZE`コマンドを使用してください。

```
YOURLIB/ANALYZE TABLE('MYLIB/SALES') QUESTION('売上の傾向を分析して')
```

結果は `QTEMP.GEMINI` に格納されます：

```sql
SELECT * FROM QTEMP.GEMINI ORDER BY SEQ
```

### API-BRIDGEから実行

API-BRIDGEから実行する場合は、`ANALYZEC`のCLプログラムを呼び出してください。

| パラメータ | 型 | 長さ | 説明 |
|------------|-----|------|------|
| TABLE | *CHAR | 50 | 分析対象テーブル（例：MYLIB/SALES） |
| QUESTION | *CHAR | 200 | 質問（例：売上の傾向を分析して） |

結果はコマンドから実行した場合と同様です。

### テーブル構造

```sql
QTEMP.GEMINI (
    SEQ INT,                          -- 行番号
    RESULT VARCHAR(2048) CCSID 1208   -- 結果テキスト
)
```
> 同じレイアウトのSQLはcreate_gemini.sqlに書かれています。物理ファイルが必要な場合はそちらを利用してください

## サンプルデータの投入

### 1. テーブル作成

IFSに`create_sales.sql`を配置し、CCSIDを設定後、実行：
> SQLに書かれているライブラリ名は変更してください

```bash
setccsid 1208 /home/blog/gemini/create_sales.sql
```

```
RUNSQLSTM SRCSTMF('/home/blog/gemini/create_sales.sql') COMMIT(*NONE)
```

### 2. データ投入

IFSに`insert_sales.sql`を配置し、CCSIDを設定後、実行：
> SQLに書かれているライブラリ名は変更してください

```bash
setccsid 1208 /home/blog/gemini/insert_sales.sql
```

```
RUNSQLSTM SRCSTMF('/home/blog/gemini/insert_sales.sql') COMMIT(*NONE)
```

### サンプルデータの実行結果

sample_apibridge_result/as400-gemini-bridge-result.json に、サンプルデータに対して「売上の傾向を分析して」と質問した結果のJSONファイルがあります。


## 注意事項

- APIタイムアウト: 2分
- エラー発生時はエラーメッセージがQTEMP.GEMINIに格納されます
- IFSファイルのCCSIDは1208（UTF-8）に設定してください
- analyze.pyでは出力されるデータは5000件を上限にしています。必要なら増やしてください
- `google-genai`が使うパッケージにRustコンパイルが必要なものがあるためAS/400ではビルドできません。そのためanalyze.pyでは直接REST APIを呼び出しています
- 分析対象データはフィールドにラベルがあればラベル、なければ物理名が使用されます。質問を書く際はフィールドの表示名を意識してください
