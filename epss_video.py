from manim import *
import os

# 設定圖片所在的資料夾路徑 (相對於這個 script 的位置)
FRAMES_DIR = "assets/frames"
# 設定每一幀圖片要停留幾秒 (秒數越小，影片速度越快)
# 0.1 秒大約是每秒 10 張圖 (10 fps)，100張圖約 10 秒鐘
FRAME_DURATION = 0.5

class EPSS_Timelapse(Scene):
    def construct(self):
        # --- 1. 準備工作 ---
        print(f"🚀 開始讀取圖片資料夾: {FRAMES_DIR}...")
        
        # 讀取資料夾中所有 .png 檔案，並確保它們是照檔名排序的
        image_files = sorted([
            f for f in os.listdir(FRAMES_DIR) 
            if f.endswith(".png") or f.endswith(".jpg")
        ])

        if not image_files:
            print("❌ 錯誤：在指定的資料夾中找不到圖片！")
            return

        print(f"📊 總共找到 {len(image_files)} 張圖片，準備合成影片。")

        # --- 2. 加入標題 (Manim 的強項，讓影片更專業) ---
        # 建立一個標題物件，放在畫面最上方
        title = Title("EPSS 30-Day Rolling Window Evolution (Past 100 Days)")
        # 使用 Write 動畫效果寫出標題
        self.play(Write(title), run_time=1.5)
        
        # --- 3. 圖片輪播核心迴圈 ---
        # 建立一個佔位符，用來記錄上一張圖片 (為了稍後移除它)
        current_image_mobject = None

        for i, img_filename in enumerate(image_files):
            # 組合完整的圖片路徑
            img_path = os.path.join(FRAMES_DIR, img_filename)
            
            # 建立 Manim 的圖片物件 (ImageMobject)
            new_image = ImageMobject(img_path)
            
            # 調整圖片大小與位置
            # 讓圖片寬度稍微小於畫面寬度
            new_image.scale_to_fit_width(config.frame_width - 1)
            # 把圖片放在標題的下方 (靠下對齊，然後往上移一點點留邊距)
            new_image.to_edge(DOWN, buff=0.5)

            if i == 0:
                # 如果是第一張圖，直接顯示
                self.add(new_image)
            else:
                # 如果不是第一張，把「上一張」移除，換成「新的一張」
                # 使用 remove 和 add 可以達成瞬間切換的效果
                self.remove(current_image_mobject)
                self.add(new_image)
            
            # 更新目前的圖片紀錄
            current_image_mobject = new_image
            
            # 停留指定的時間 (這就是控制影片速度的關鍵)
            self.wait(FRAME_DURATION)
            
            # (選用) 在終端機顯示進度
            if (i + 1) % 10 == 0:
                 print(f"--- 已處理進度: {i+1}/{len(image_files)} 幀 ---")

        # --- 4. 結尾 ---
        # 影片結束時，最後一張圖多停留 2 秒，讓觀眾看清楚
        self.wait(2)
        # 最後用淡出效果結束標題和圖片
        self.play(
            FadeOut(current_image_mobject),
            FadeOut(title)
        )