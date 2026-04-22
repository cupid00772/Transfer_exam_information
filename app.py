import os
from datetime import date
from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pydantic import BaseModel
from dotenv import load_dotenv
import google.generativeai as genai

from models.database import init_db, get_db, School, Department, ExamInfo, ChatSession, ChatMessage

# 載入 .env 檔案
load_dotenv()

app = FastAPI(title="實時轉學考資訊系統")

# 初始化資料庫
init_db()

# 設定模板目錄
os.makedirs("templates", exist_ok=True)
templates = Jinja2Templates(directory="templates")

# 設定 Gemini API Key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    print("WARNING: GEMINI_API_KEY is not set. Chat function will not work properly.")

class ChatRequest(BaseModel):
    session_token: str
    message: str

def seed_data(db: Session):
    """如果資料庫沒有學校資料，自動塞入一些假資料供測試"""
    if db.query(School).count() == 0:
        ntu = School(name="國立台灣大學 (台大)", region="北區", website_url="https://www.ntu.edu.tw")
        ust = School(name="台灣聯合大學系統 (台聯大)", region="跨區", website_url="https://www.ust.edu.tw")
        tcus = School(name="台灣綜合大學系統 (台綜大)", region="跨區", website_url="https://www.tcus.edu.tw")
        nccu = School(name="國立政治大學 (政大)", region="北區", website_url="https://www.nccu.edu.tw")
        
        db.add_all([ntu, ust, tcus, nccu])
        db.commit()
        
        dept_ntu = Department(school_id=ntu.id, name="資訊工程學系")
        dept_ust = Department(school_id=ust.id, name="電機類組 (A3)")
        dept_tcus = Department(school_id=tcus.id, name="資工類組 (E1)")
        dept_nccu = Department(school_id=nccu.id, name="企業管理學系")
        
        db.add_all([dept_ntu, dept_ust, dept_tcus, dept_nccu])
        db.commit()
        
        exam_ntu = ExamInfo(
            department_id=dept_ntu.id, year=115, semester="暑轉",
            apply_start_date=date(2026, 5, 5), apply_end_date=date(2026, 5, 20), exam_date=date(2026, 7, 15),
            quota=100, restrictions="請詳閱台灣大學招生簡章，依各學系規定為主。", brochure_url="https://www.aca.ntu.edu.tw/WebUPD/aca/LocalAdmissionClass/115%E8%BD%89%E5%AD%B8%E8%80%83%E5%90%8D%E9%A1%8D%E5%8F%8A%E7%A7%91%E7%9B%AE%E5%85%AC%E5%91%8A.pdf"
        )
        exam_ust = ExamInfo(
            department_id=dept_ust.id, year=115, semester="暑轉",
            apply_start_date=date(2026, 5, 10), apply_end_date=date(2026, 5, 25), exam_date=date(2026, 7, 12),
            quota=250, restrictions="採學群聯合招生，請詳閱台聯大115學年度轉學考簡章。", brochure_url="https://exam.nycu.edu.tw/UST/115/115%E5%AD%B8%E5%B9%B4%E5%BA%A6%E5%8F%B0%E8%81%AF%E5%A4%A7%E8%BD%89%E5%AD%B8%E8%80%83%E7%B0%A1%E7%AB%A0.pdf"
        )
        exam_tcus = ExamInfo(
            department_id=dept_tcus.id, year=115, semester="暑轉",
            apply_start_date=date(2026, 5, 15), apply_end_date=date(2026, 5, 30), exam_date=date(2026, 7, 20),
            quota=200, restrictions="台綜大(成大/中興/中山/中正)聯合招生，一次筆試，可填多個志願。", brochure_url="https://exam-tcustrans.nsysu.edu.tw/static/file/66/1066/img/671805059.pdf"
        )
        exam_nccu = ExamInfo(
            department_id=dept_nccu.id, year=115, semester="暑轉",
            apply_start_date=date(2026, 5, 1), apply_end_date=date(2026, 5, 15), exam_date=date(2026, 7, 10),
            quota=50, restrictions="各系標準不同，部分科系需繳交書面審查與面試。", brochure_url="https://www.nccu.edu.tw/app/index.php?Action=downloadfile&file=WVhSMFlXTm9MelkxTDNCMFlWODFORFk1WHpnMk9ETXpPREpmT1RrMU5EUXVjR1Jt&fname=WW54RPOKIC4441MPHCLKRKZWQOTWWT14QO3435HGTX25LK40FCNKA0540054USSSSSWWHHLPA404ROJGKOSWTSLOOPB0WSGCNPRLXWA0ROA401B4US00YWFCNPPOPPKKDGA0SW14ZSNKDCWSUSB0YSICLP35PKTSROECUSQOWSTSRKB0DGTSPLJHEDXWPK10&cg=88"
        )
        
        db.add_all([exam_ntu, exam_ust, exam_tcus, exam_nccu])
        db.commit()

@app.on_event("startup")
def on_startup():
    db = next(get_db())
    seed_data(db)

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/api/search")
def search_exam_info(keyword: str = "", db: Session = Depends(get_db)):
    """搜尋轉學考資訊"""
    results = []
    
    # 搜尋學校或科系名稱
    schools = db.query(School).filter(School.name.like(f"%{keyword}%")).all()
    departments = db.query(Department).filter(Department.name.like(f"%{keyword}%")).all()
    
    # 收集相關的 ExamInfo
    exam_infos = []
    for school in schools:
        for dept in school.departments:
            exam_infos.extend(dept.exam_infos)
            
    for dept in departments:
        # 避免重複
        if dept.exam_infos[0] not in exam_infos if dept.exam_infos else False:
            exam_infos.extend(dept.exam_infos)
            
    # 如果都沒關鍵字，回傳全部 (測試用)
    if not keyword:
        exam_infos = db.query(ExamInfo).all()
        
    for info in exam_infos:
        dept = info.department
        school = dept.school
        results.append({
            "school_name": school.name,
            "year": info.year,
            "semester": info.semester,
            "apply_period": f"{info.apply_start_date} ~ {info.apply_end_date}",
            "exam_date": str(info.exam_date),
            "quota": info.quota,
            "restrictions": info.restrictions,
            "brochure_url": info.brochure_url,
            "updated_at": info.updated_at.strftime("%Y-%m-%d %H:%M:%S")
        })
        
    return {"status": "success", "data": results}

@app.post("/api/chat")
async def chat_with_ai(req: ChatRequest, db: Session = Depends(get_db)):
    """與 Gemini AI 聊天，使用資料庫內的資訊作為 RAG"""
    if not GEMINI_API_KEY:
        return {"status": "error", "reply": "系統尚未設定 Gemini API Key，無法提供 AI 服務。"}
        
    # 取得或建立 Session
    session = db.query(ChatSession).filter(ChatSession.session_token == req.session_token).first()
    if not session:
        session = ChatSession(session_token=req.session_token)
        db.add(session)
        db.commit()
        db.refresh(session)
        
    # 儲存使用者訊息
    user_msg = ChatMessage(chat_session_id=session.id, role="user", content=req.message)
    db.add(user_msg)
    db.commit()
    
    # RAG: 取得所有資料庫內的轉學考資訊作為 Context
    all_exams = db.query(ExamInfo).all()
    context_str = "目前系統內有以下轉學考資訊：\n"
    for info in all_exams:
        school = info.department.school
        context_str += f"- {school.name} ({info.year}{info.semester}): 報名 {info.apply_start_date}~{info.apply_end_date}, 考試 {info.exam_date}, 簡章: {info.brochure_url}\n"
        
    prompt = f"你是一個專業的轉學考顧問。請根據以下系統資料回答使用者的問題。如果資料中沒有提到，請誠實說不知道，不要亂編。\n\n資料：\n{context_str}\n\n使用者問題：{req.message}"
    
    try:
        model = genai.GenerativeModel('gemini-3.1-flash-lite-preview')
        response = model.generate_content(prompt)
        ai_reply = response.text
        
        # 儲存 AI 回應
        ai_msg = ChatMessage(chat_session_id=session.id, role="assistant", content=ai_reply)
        db.add(ai_msg)
        db.commit()
        
        return {"status": "success", "reply": ai_reply}
    except Exception as e:
        return {"status": "error", "reply": f"AI 服務發生錯誤: {str(e)}"}
