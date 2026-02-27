import requests
import duckdb
import pandas as pd
from datetime import date, timedelta
import io
import gzip
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# ================= 設定區 =================
DB_NAME = 'epss_research.db'
START_DATE = date(2021, 4, 14)
END_DATE = date.today()
MAX_WORKERS = 4  # 同時開 4 個下載通道 (建議不要超過 5，以免被伺服器封鎖)
# =========================================

def get_model_version(report_date):
    d = report_date
    if d < date(2022, 2, 4): return "v1"
    elif d < date(2023, 3, 7): return "v2"
    elif d < date(2025, 3, 17): return "v3" # 設定 V3 截止日
    else: return "v4" # 之後的都是 v4

def init_db(con):
    con.execute("""
        CREATE TABLE IF NOT EXISTS epss_scores (
            cve_id VARCHAR,
            epss DOUBLE,
            percentile DOUBLE,
            report_date DATE,
            model_version VARCHAR
        );
    """)
    # 這裡先不建索引，等全部跑完再建會比較快
    
def get_existing_dates(con):
    try:
        result = con.sql("SELECT DISTINCT report_date FROM epss_scores").fetchall()
        return {row[0] for row in result}
    except:
        return set()

# 這是工人的工作：只負責下載跟處理資料，不負責寫入資料庫
def download_task(target_date):
    date_str = target_date.strftime("%Y-%m-%d")
    url = f"https://epss.empiricalsecurity.com/epss_scores-{date_str}.csv.gz"
    
    try:
        # 設定 timeout，避免卡死
        response = requests.get(url, stream=True, timeout=20)
        
        if response.status_code == 200:
            with gzip.open(io.BytesIO(response.content), 'rt') as f:
                df = pd.read_csv(f, comment='#')
            
            # 資料清洗
            df.columns = [c.strip() for c in df.columns]
            if 'cve' in df.columns: df.rename(columns={'cve': 'cve_id'}, inplace=True)
            if 'percentile' not in df.columns: df['percentile'] = None
            
            df['report_date'] = target_date
            df['model_version'] = get_model_version(target_date)
            
            # 只保留需要的欄位
            final_df = df[['cve_id', 'epss', 'percentile', 'report_date', 'model_version']]
            return (target_date, final_df, "OK")
        else:
            return (target_date, None, f"HTTP {response.status_code}")
            
    except Exception as e:
        return (target_date, None, str(e))

def main():
    print(f"[*] 啟動極速多執行緒模式 (Workers: {MAX_WORKERS})")
    
    con = duckdb.connect(DB_NAME)
    init_db(con)
    
    existing = get_existing_dates(con)
    print(f"[*] 資料庫已有 {len(existing)} 天數據，準備補齊...")
    
    # 產生任務清單 (過濾掉已經有的)
    todo_dates = []
    curr = START_DATE
    while curr <= END_DATE:
        if curr not in existing:
            todo_dates.append(curr)
        curr += timedelta(days=1)
    
    print(f"[*] 尚有 {len(todo_dates)} 天需要下載。")
    print("-" * 50)

    # 批次處理，每 100 天存檔一次，避免記憶體爆掉
    BATCH_SIZE = 100 
    total_processed = 0

    # 使用 ThreadPoolExecutor 進行並行下載
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # 將任務分批送出
        for i in range(0, len(todo_dates), BATCH_SIZE):
            batch_dates = todo_dates[i : i + BATCH_SIZE]
            
            # 送出這一批的任務
            future_to_date = {executor.submit(download_task, d): d for d in batch_dates}
            
            con.execute("BEGIN TRANSACTION")
            
            for future in as_completed(future_to_date):
                d = future_to_date[future]
                try:
                    date_res, df, status = future.result()
                    date_str = date_res.strftime("%Y-%m-%d")
                    
                    if status == "OK" and df is not None:
                        con.execute("INSERT INTO epss_scores SELECT * FROM df")
                        print(f"[{date_str}] 下載完成 | {len(df)} 筆")
                    else:
                        print(f"[{date_str}] 跳過: {status}")
                        
                except Exception as exc:
                    print(f"[{d}] 執行緒錯誤: {exc}")

            con.execute("COMMIT")
            print(f"--- [系統] 已儲存進度 (目前累積完成 {i + len(batch_dates)} 天) ---")

    # 最後建立索引 (這步會花一點時間，但能讓查詢變超快)
    print("[*] 正在建立索引 (Optimize)...")
    con.execute("CREATE INDEX IF NOT EXISTS idx_cve ON epss_scores(cve_id)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_date ON epss_scores(report_date)")
    
    con.close()
    print("[*] 全部作業完成！")

if __name__ == "__main__":
    main()