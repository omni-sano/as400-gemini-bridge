-- 結果格納用テーブル（CLプログラムはQTEMPに自動作成）
-- 永続化が必要な場合はこちらを使用
CREATE OR REPLACE TABLE YOURLIB.GEMINI (
    SEQ INT,
    RESULT VARCHAR(2048) CCSID 1208
)
