import os
import sys
import re
import json
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime, date
from dotenv import load_dotenv

# 確保可以 import 上一層的 models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import SessionLocal, School, Department, ExamInfo

# 載入環境變數與設定 Gemini
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    import google.generativeai as genai
    genai.configure(api_key=GEMINI_API_KEY)

def download_pdf(url, filepath):
    """下載 PDF 到本地"""
    print(f"  📥 正在下載 PDF: {url}")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }
    # verify=False 忽略部分大學網站 SSL 憑證問題
    response = requests.get(url, headers=headers, stream=True, verify=False, timeout=60)
    response.raise_for_status()
    with open(filepath, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    return filepath

def extract_info_with_gemini(filepath):
    """使用 Gemini 解析 PDF 並回傳 JSON"""
    if not GEMINI_API_KEY:
        raise ValueError("沒有 GEMINI_API_KEY，無法執行 AI 解析。")
        
    print(f"  🧠 正在上傳 PDF 交由 Gemini 分析 (可能需要幾十秒)...")
    uploaded_file = genai.upload_file(path=filepath, display_name="brochure")
    
    # 建立 model (使用 3.1 flash lite preview)
    model = genai.GenerativeModel('gemini-3.1-flash-lite-preview')
    
    prompt = """
    你是一個專業的資料萃取 AI。請閱讀這份轉學考簡章，並以嚴格的 JSON 格式輸出以下五項資訊：
    {
      "apply_start_date": "YYYY-MM-DD", (報名開始日期，例如 2026-05-01。若無確切年份請用 2026)
      "apply_end_date": "YYYY-MM-DD", (報名結束日期)
      "exam_date": "YYYY-MM-DD", (筆試日期，若無筆試請填 null)
      "quota": 100, (整份簡章所有科系的「總招生名額」加總，請給出一個整數數字)
      "restrictions": "字串" (簡要總結共同的報名資格或限制，50字以內)
    }
    請注意：只輸出純 JSON 字串，不要包含 ```json 標籤，也不要有任何其他多餘文字。
    如果簡章中找不到精確日期，請盡量根據上下文推斷。
    """
    
    response = model.generate_content([uploaded_file, prompt])
    
    # 刪除上傳的檔案以節省雲端空間
    genai.delete_file(uploaded_file.name)
    
    # 嘗試解析 JSON
    text = response.text.strip()
    if text.startswith("```json"):
        text = text[7:-3].strip()
    elif text.startswith("```"):
        text = text[3:-3].strip()
        
    return json.loads(text)

def scrape_all_exams():
    print("開始執行全台轉學考爬蟲 (AI 增強版)...")
    
    targets = [
        {
            "school_keyword": "台聯大",
            "url": "https://exam.nycu.edu.tw/UST/",
            "direct_pdf": "https://exam.nycu.edu.tw/UST/115/115%E5%AD%B8%E5%B9%B4%E5%BA%A6%E5%8F%B0%E8%81%AF%E5%A4%A7%E8%BD%89%E5%AD%B8%E8%80%83%E7%B0%A1%E7%AB%A0.pdf",
            "year": 115
        },
        {
            "school_keyword": "台綜大",
            "url": "https://exam-tcustrans.nsysu.edu.tw/",
            "direct_pdf": "https://exam-tcustrans.nsysu.edu.tw/static/file/66/1066/img/671805059.pdf",
            "year": 115
        },
        {
            "school_keyword": "台大",
            "url": "https://www.aca.ntu.edu.tw/w/aca/LocalAdmissionClass_21072014054302121",
            "direct_pdf": "https://www.aca.ntu.edu.tw/WebUPD/aca/LocalAdmissionClass/115%E8%BD%89%E5%AD%B8%E8%80%83%E5%90%8D%E9%A1%8D%E5%8F%8A%E7%A7%91%E7%9B%AE%E5%85%AC%E5%91%8A.pdf",
            "year": 115
        },
        {
            "school_keyword": "政大",
            "url": "https://www.nccu.edu.tw/p/406-1000-22278,r124.php?Lang=zh-tw",
            "direct_pdf": "https://www.nccu.edu.tw/app/index.php?Action=downloadfile&file=WVhSMFlXTm9MelkxTDNCMFlWODFORFk1WHpnMk9ETXpPREpmT1RrMU5EUXVjR1Jt&fname=WW54RPOKIC4441MPHCLKRKZWQOTWWT14QO3435HGTX25LK40FCNKA0540054USSSSSWWHHLPA404ROJGKOSWTSLOOPB0WSGCNPRLXWA0ROA401B4US00YWFCNPPOPPKKDGA0SW14ZSNKDCWSUSB0YSICLP35PKTSROECUSQOWSTSRKB0DGTSPLJHEDXWPK10&cg=88",
            "year": 115
        }
    ]
    
    # 建立暫存資料夾
    temp_dir = os.path.join(os.path.dirname(__file__), "temp_brochures")
    os.makedirs(temp_dir, exist_ok=True)
    
    for target in targets:
        print(f"\n🔍 正在處理 {target['school_keyword']} {target['year']}學年度簡章...")
        brochure_url = target["direct_pdf"]
        
        # 預設資料 (若 AI 萃取失敗時的備案)
        exam_data = {
            "apply_start_date": date(target['year'] + 1911, 5, 10),
            "apply_end_date": date(target['year'] + 1911, 5, 25),
            "exam_date": date(target['year'] + 1911, 7, 10),
            "quota": 0,
            "restrictions": "[系統預設] 請詳閱最新簡章內容。"
        }
        
        pdf_path = os.path.join(temp_dir, f"{target['school_keyword']}_{target['year']}.pdf")
        
        try:
            # 1. 下載 PDF
            download_pdf(brochure_url, pdf_path)
            
            # 2. AI 萃取
            ai_data = extract_info_with_gemini(pdf_path)
            print(f"  ✨ AI 萃取成功: {ai_data}")
            
            # 3. 覆寫預設資料 (需處理日期格式字串轉換)
            if ai_data.get("apply_start_date") and ai_data["apply_start_date"] != "null":
                exam_data["apply_start_date"] = datetime.strptime(ai_data["apply_start_date"], "%Y-%m-%d").date()
            if ai_data.get("apply_end_date") and ai_data["apply_end_date"] != "null":
                exam_data["apply_end_date"] = datetime.strptime(ai_data["apply_end_date"], "%Y-%m-%d").date()
            if ai_data.get("exam_date") and ai_data["exam_date"] != "null":
                try:
                    exam_data["exam_date"] = datetime.strptime(ai_data["exam_date"], "%Y-%m-%d").date()
                except Exception:
                    exam_data["exam_date"] = None
            if ai_data.get("quota") is not None:
                exam_data["quota"] = int(ai_data["quota"])
            if ai_data.get("restrictions"):
                exam_data["restrictions"] = ai_data["restrictions"]
                
        except Exception as e:
            print(f"  ⚠️ 處理 PDF 時發生錯誤 ({e})，將使用預設資料寫入資料庫。")
            
        # 4. 寫入資料庫
        update_database(target['school_keyword'], target['year'], brochure_url, exam_data)
        
        # 刪除本地暫存 PDF
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
            
        # 暫停一下避免打滿 API Rate Limit
        time.sleep(3)

def update_database(school_keyword, year, brochure_url, exam_data):
    """將資料更新至資料庫"""
    db = SessionLocal()
    try:
        school = db.query(School).filter(School.name.like(f"%{school_keyword}%")).first()
        if not school:
            print(f"❌ 找不到學校: {school_keyword}")
            return
            
        depts = db.query(Department).filter(Department.school_id == school.id).all()
        for dept in depts:
            exam = db.query(ExamInfo).filter(ExamInfo.department_id == dept.id, ExamInfo.year == year).first()
            if exam:
                exam.brochure_url = brochure_url
                exam.apply_start_date = exam_data["apply_start_date"]
                exam.apply_end_date = exam_data["apply_end_date"]
                exam.exam_date = exam_data["exam_date"]
                exam.quota = exam_data["quota"]
                exam.restrictions = exam_data["restrictions"]
                exam.updated_at = datetime.now()
            else:
                exam = ExamInfo(
                    department_id=dept.id,
                    year=year,
                    semester="暑轉",
                    apply_start_date=exam_data["apply_start_date"],
                    apply_end_date=exam_data["apply_end_date"],
                    exam_date=exam_data["exam_date"],
                    quota=exam_data["quota"],
                    restrictions=exam_data["restrictions"],
                    brochure_url=brochure_url
                )
                db.add(exam)
        db.commit()
        print(f"✅ 成功將 {school.name} 的資料庫紀錄更新為 AI 萃取結果！")
    except Exception as e:
        print(f"❌ 寫入資料庫失敗: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    scrape_all_exams()
