import duckdb
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import os
from adjustText import adjust_text
from datetime import datetime, timedelta, date

# ================= 設定區 =================
DB_PATH = r"D:\EPSS\epss_research.db"
OUTPUT_DIR = "frames"  # 圖片輸出資料夾
DAYS_TO_GENERATE = 100 # 要生成幾張圖 (往回跑幾天)
# =========================================

def ensure_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def generate_frame(con, target_date, frame_index):
    """
    畫出指定日期 (target_date) 的 30 天散佈圖
    """
    print(f"[{frame_index+1}/{DAYS_TO_GENERATE}] 正在繪製 {target_date} 的圖表...")

    # SQL: 找出 target_date 當天回推 30 天內的數據
    sql = f"""
        WITH FirstSeen AS (
            SELECT 
                cve_id,
                MIN(report_date) as publish_date
            FROM epss_scores
            WHERE cve_id > 'CVE-2023' 
            GROUP BY cve_id
        ),
        TargetDayScores AS (
            SELECT cve_id, epss
            FROM epss_scores
            WHERE report_date = '{target_date}'
        )
        SELECT 
            F.cve_id,
            F.publish_date,
            L.epss
        FROM FirstSeen F
        JOIN TargetDayScores L ON F.cve_id = L.cve_id
        WHERE F.publish_date BETWEEN CAST('{target_date}' AS DATE) - INTERVAL 30 DAY AND CAST('{target_date}' AS DATE)
        ORDER BY L.epss DESC
    """
    df = con.execute(sql).df()

    # 準備畫布
    fig, ax = plt.subplots(figsize=(15, 8), dpi=100)
    
    if df.empty:
        print(f"   ⚠️ {target_date} 沒有資料，跳過繪製內容。")
        ax.text(0.5, 0.5, "No Data Available", ha='center', fontsize=20)
        ax.set_title(f"EPSS Report: {target_date}", fontsize=16, fontweight='bold', loc='left', pad=20)
    else:
        dates_num = mdates.date2num(df['publish_date'])
        jitter = np.random.uniform(-0.25, 0.25, size=len(dates_num))
        df['jittered_x'] = dates_num + jitter

        ax.scatter(df['jittered_x'], df['epss'], alpha=0.5, s=40, c='#4682B4', edgecolors='none', zorder=2)

        texts = []
        df_labeled = df[df['epss'] >= 0.01].copy()

        for _, row in df_labeled.iterrows():
            t = ax.text(
                row['jittered_x'], 
                row['epss'] + 0.01,
                row['cve_id'], 
                fontsize=8,
                color='#333333',
                ha='center',
                va='bottom',
                bbox=dict(boxstyle="round,pad=0.1", fc="white", ec="none", alpha=0.7),
                zorder=3
            )
            texts.append(t)

        if len(texts) > 0:
            try:
                adjust_text(texts, x=df['jittered_x'], y=df['epss'],
                            arrowprops=dict(arrowstyle='-', color='#aaaaaa', lw=0.8),
                            force_points=0.2, force_text=0.4, lim=20)
            except Exception as e:
                print(f"   ⚠️ adjust_text 警告: {e} (這通常沒關係)")

        # 裝飾圖表
        ax.set_title(f"EPSS Report: {target_date} (Last 30 Days)", fontsize=16, fontweight='bold', loc='left', pad=20)
        subtitle_text = "Rolling 30-day window. Only labeling EPSS > 1%."
        ax.text(0.0, 1.01, subtitle_text, transform=ax.transAxes, fontsize=10, style='italic', color='#555555')

        ax.set_ylabel("EPSS Score", fontsize=12)
        ax.set_ylim(-0.02, 1.05)
        ax.set_yticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])
        ax.set_yticklabels(['0%', '20%', '40%', '60%', '80%', '100%'])
        
        # 動態 X 軸範圍 (確保格式轉換正確)
        target_dt = datetime.strptime(str(target_date), '%Y-%m-%d')
        start_dt = target_dt - timedelta(days=31)
        ax.set_xlim(start_dt, target_dt + timedelta(days=1))
        
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=3))
        
        ax.grid(True, linestyle='-', alpha=0.15)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

    filename = os.path.join(OUTPUT_DIR, f"frame_{frame_index:03d}_{target_date}.png")
    plt.tight_layout()
    plt.savefig(filename)
    plt.close(fig)

def main():
    if not os.path.exists(DB_PATH):
        print("❌ 找不到資料庫！")
        return

    ensure_dir(OUTPUT_DIR)
    con = duckdb.connect(DB_PATH, read_only=True)

    # 1. 取得資料庫最新日期
    latest_date_row = con.execute("SELECT MAX(report_date) FROM epss_scores").fetchone()
    if not latest_date_row or not latest_date_row[0]:
        print("⚠️ 資料庫是空的。")
        return
    
    # 【關鍵修正區】
    raw_date = latest_date_row[0]
    
    # 檢查取出來的到底是「字串」還是「日期物件」
    if isinstance(raw_date, (date, datetime)):
        # 如果已經是日期物件，直接用
        db_latest_date = raw_date
    else:
        # 如果是字串，才進行解析
        db_latest_date = datetime.strptime(str(raw_date), '%Y-%m-%d').date()
    
    print(f"📅 資料庫最新日期: {db_latest_date}")
    print(f"🚀 準備生成 {DAYS_TO_GENERATE} 張連續圖片...")

    # 2. 迴圈生成
    for i in range(DAYS_TO_GENERATE):
        days_offset = (DAYS_TO_GENERATE - 1) - i
        
        # timedelta 可以直接跟 date 物件運算
        target_date_obj = db_latest_date - timedelta(days=days_offset)
        target_date_str = target_date_obj.strftime('%Y-%m-%d')
        
        generate_frame(con, target_date_str, i)

    print(f"\n✅ 全部完成！圖片已儲存於 '{OUTPUT_DIR}' 資料夾。")
    con.close()
    
    os.startfile(OUTPUT_DIR)

if __name__ == "__main__":
    main()