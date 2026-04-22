# 🎓 轉學考資訊與 AI 諮詢系統 (Transfer Exam Information System)
<img width="1913" height="946" alt="image" src="https://github.com/user-attachments/assets/1d40cc1e-5f15-4688-80e0-5975d87d953d" />

> **作業性質**：個人作業 (基於 Antigravity Skill 設計)
> **專案目標**：打造一個整合爬蟲、RAG 與 LLM 應用的全端系統

本專案是一個**實時轉學考資訊平台**，整合了台灣主要大學系統（台聯大、台綜大、台大、政大）的轉學考簡章資訊。
系統具備**「自動化 AI 爬蟲」**能直接下載長篇官方簡章 PDF，並利用 Gemini AI 萃取出報名時間與名額；同時內建**「RAG 智慧顧問」**，讓使用者能夠直接透過聊天介面詢問轉學考相關問題，AI 會根據最新的資料庫數據給出精確回答。

---

## ✨ 核心功能 (Features)

| 功能模組 | 說明 | 實作狀態 |
| :--- | :--- | :---: |
| **響應式資訊儀表板** | 乾淨直覺的前端介面，一覽各校最新的報名日期與招生名額 | ✅ 完成 |
| **自動化 AI 爬蟲** | `crawler/ust_scraper.py` 自動下載各大校系 PDF 簡章 | ✅ 完成 |
| **PDF 語意解析** | 結合 Gemini 1.5/3.1 Flash，將幾十頁的簡章自動轉換為結構化 JSON 資料寫入 DB | ✅ 完成 |
| **RAG 智慧諮詢助理** | 將資料庫內容轉為 Context，讓使用者透過聊天室詢問轉學考細節，解決幻覺問題 | ✅ 完成 |
| **對話狀態管理** | 支援多聊天室（session），維持上下文脈絡 | ✅ 完成 |

---

## 📂 專案結構 (Project Structure)

```text
Transfer_exam_information/
├── .agents/
│   └── skills/                ← 輔助開發的 AI Skill 定義 (prd, architecture, models 等)
├── crawler/
│   └── ust_scraper.py         ← 核心：自動下載 PDF 並呼叫 Gemini 萃取資料的 AI 爬蟲
├── docs/                      
│   ├── PRD.md                 ← 產品需求文件
│   ├── ARCHITECTURE.md        ← 系統架構設計
│   └── MODELS.md              ← 資料庫綱要設計
├── models/
│   └── database.py            ← SQLite 資料表定義 (使用 SQLAlchemy)
├── templates/
│   └── index.html             ← 前端介面 (純 JS/CSS + Jinja2 渲染)
├── screenshots/               ← 系統展示截圖存放區
├── app.py                     ← FastAPI 主程式 (包含 API 路由、RAG 邏輯、資料庫初始化)
├── requirements.txt           ← Python 相依套件清單
├── .env                       ← 環境變數設定檔 (存放 GEMINI_API_KEY)
└── README.md                  ← 本專案說明文件與心得報告
```

---

## 🚀 快速啟動 (Quick Start)

### 1. 環境設定與安裝
```bash
# 建立並啟動虛擬環境
python3 -m venv .venv
source .venv/bin/activate   # Windows 請使用: .venv\Scripts\activate

# 安裝所需套件
pip install -r requirements.txt
```

### 2. 環境變數設定
請在專案根目錄建立 `.env` 檔案，並填入你的 Gemini API Key：
```env
GEMINI_API_KEY=你的_API_KEY
```

### 3. 啟動伺服器與資料庫初始化
第一次啟動時，系統會自動建立 `transfer_exam.db` 並寫入基礎測試資料。
```bash
uvicorn app:app --reload
```
開啟瀏覽器前往：[http://localhost:8000](http://localhost:8000)

### 4. 執行終極 AI 爬蟲 (抓取真實 PDF 資料)
另外開一個終端機視窗，執行爬蟲程式。它會自動下載台大、政大、台聯大、台綜大的真實簡章，交由 Gemini 解析後覆寫資料庫。
```bash
python crawler/ust_scraper.py
```
執行完畢後，回到網頁重新整理，即可看到最新的官方簡章數據！

---

## 📝 心得報告

**姓名**：[張承新]
**學號**：[D1285325]

### 問題與反思

**Q1. 你設計的哪一個 Skill 效果最好？為什麼？哪一個效果最差？你認為原因是什麼？**

> **效果最好的 Skill 是 `[/implement]`**：因為在執行這步之前，我們已經透過 `[/prd]`、`[/architecture]` 和 `[/models]` 打下了非常穩固的文件基礎。當 AI 清楚知道整個系統架構跟資料庫綱要後，生成的 FastAPI 後端與 HTML 前端程式碼結構非常完整，這讓我深刻體會到「設計文件」對於引導 AI 的重要性。
>
> **效果較差的 Skill 是 `[/test]`**：這項技能大多時候只能產出一份「手動測試清單」，並無法真的代替我進行系統層面的操作。因為 AI 缺乏直接的瀏覽器點擊與畫面確認能力，最後還是需要我親自根據清單一步一步驗證 UI 畫面與爬蟲的真實效果。

---

**Q2. 在用 AI 產生程式碼的過程中，你遇到什麼問題是 AI 沒辦法自己解決、需要你介入處理的？**

> 1. **套件版本相容性與語法過時**：AI 產生的程式碼有時會基於舊版的語法。例如在實作 FastAPI 渲染 Jinja2 模板時，遇到了 `TemplateResponse` 語法不支援字典解包的報錯；這時 AI 無法事先預知環境版本，需要我將終端機的錯誤訊息 (TypeError) 貼給它看，它才能修正為最新寫法。
> 2. **爬蟲與真實網頁的落差**：一開始希望 AI 直接寫出能爬台聯大簡章的程式，但 AI 根本無法事先知道真實學校網站複雜的 DOM 結構或是隱藏的真實 PDF 連結。最後是我主動提供真實的網址，並介入調整架構，讓爬蟲下載 PDF 後直接交由 Gemini API 去做語意解析，才成功繞過了傳統爬蟲解析表格的死胡同！
