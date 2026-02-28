## 🛠️ 環境建置 (Prerequisites)

在執行本專案之前，請確保您的系統已安裝以下軟體：

### 1. 系統需求的軟體
* **[FFmpeg](https://ffmpeg.org/)**：Manim 的核心影片合成引擎 (需自行手動加入系統環境變數 `PATH`)。
* **[MiKTeX](https://miktex.org/)** (或其他 LaTeX 發行版)：用於渲染影片中高品質的標題與數學字體。

### 2. 建立 Python 虛擬環境
為避免套件版本衝突，建議在專案目錄下建立獨立的虛擬環境。請在終端機執行以下指令：
在D槽建立一個名為EPSS的檔案
**Windows 系統:**
```bash
# 建立名為 venv 的虛擬環境
python -m venv venv

# 啟動虛擬環境 (成功後終端機提示字元前會出現 (venv))
venv\Scripts\activate
```
**macOS / Linux 系統:**

```Bash
python3 -m venv venv
source venv/bin/activate
```
### 3. 安裝python套件
確認已啟動虛擬環境 (venv) 後，執行以下指令安裝本專案所需的所有 Python 套件：

```Bash
pip install duckdb pandas matplotlib numpy adjustText manim
```
## 📂 專案架構 (Project Structure)
在D槽建立按照下列檔案位置建立資料夾或python檔
```text
📁 EPSS/
│
├── 📄 epss_database.py   # Step 1: 下載並更新 EPSS 數據至 DuckDB
├── 📄 epss_picture.py    # Step 2: 執行 SQL 查詢並生成 100 天的散佈圖 (PNG)
├──📁EPSS_Video_Project/
   │── 📁assets/
   │── 📁media/
   │── 📄epss_video.py   # Step 3: 使用 Manim 將圖片合成為高畫質影片
```
## 🚀 執行步驟 (How to Run)
請嚴格依照以下順序執行程式，即可從無到有產出動態分析影片：

**Step 1: 更新 EPSS 資料庫**
執行資料庫更新主程式，這會下載最新的 EPSS 數據並寫入本地 DuckDB 中。

```Bash
python epss_database.py
```
**Step 2: 批量生成時間軸圖表 (Generate Frames)**
此腳本會從資料庫中最新的一天開始，往回推 100 天。每一天都會執行一次複雜的 SQL 查詢與智慧避讓繪圖，產出 100 張靜態圖片。會存放在 frames 資料夾中。

```Bash
python epss_picture.py
```
**Step 3: 渲染高畫質影片 (Render Video)**
使用 Manim 讀取生成的圖片序列，加入專業的 LaTeX 標題與動畫過場，並合成為 .mp4 影片。

```Bash
manim -pqh epss_video.py EPSS_Timelapse
參數說明：-p (渲染後自動播放), -q (品質), -h (1080p 60fps 高畫質)
```
渲染完成後，影片將自動儲存於專案目錄下的 media/videos/... 資料夾中。
