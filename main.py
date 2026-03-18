from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import sqlite3, hashlib, jwt, uuid, os
from datetime import datetime, timedelta
from typing import Optional, List

app = FastAPI(title="BSS Backend API")

# CORS — allow InfinityFree frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # ganti dengan domain InfinityFree kamu setelah deploy
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SECRET  = os.getenv("JWT_SECRET", "bss-secret-key-ganti-ini-di-railway")
DB_PATH = os.getenv("DB_PATH", "bss.db")

# ── DATABASE SETUP ──
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id       TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            name     TEXT NOT NULL,
            password TEXT NOT NULL,
            created  TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS schedules (
            id       TEXT PRIMARY KEY,
            user_id  TEXT NOT NULL,
            subject  TEXT NOT NULL,
            book     TEXT,
            teacher  TEXT,
            time     TEXT,
            color    TEXT NOT NULL DEFAULT '#e63312',
            days     TEXT NOT NULL,
            created  TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)
    conn.commit()
    conn.close()

init_db()

# ── HELPERS ──
def hash_password(p: str) -> str:
    return hashlib.sha256(p.encode()).hexdigest()

def make_token(user_id: str, username: str) -> str:
    payload = {
        "sub": user_id,
        "username": username,
        "exp": datetime.utcnow() + timedelta(days=30)
    }
    return jwt.encode(payload, SECRET, algorithm="HS256")

security = HTTPBearer()

def get_current_user(creds: HTTPAuthorizationCredentials = Depends(security)):
    try:
        data = jwt.decode(creds.credentials, SECRET, algorithms=["HS256"])
        return data
    except:
        raise HTTPException(status_code=401, detail="Token tidak valid atau expired")

# ── MODELS ──
class RegisterReq(BaseModel):
    username: str
    name: str
    password: str

class LoginReq(BaseModel):
    username: str
    password: str

class ScheduleReq(BaseModel):
    id: Optional[str] = None
    subject: str
    book: Optional[str] = ""
    teacher: Optional[str] = ""
    time: Optional[str] = ""
    color: Optional[str] = "#e63312"
    days: List[int]

# ── AUTH ROUTES ──
@app.post("/auth/register")
def register(req: RegisterReq):
    if len(req.username) < 3:
        raise HTTPException(400, "Username minimal 3 karakter")
    if len(req.password) < 6:
        raise HTTPException(400, "Password minimal 6 karakter")
    if not req.username.replace("_","").isalnum():
        raise HTTPException(400, "Username hanya huruf, angka, underscore")
    
    conn = get_db()
    try:
        uid = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO users VALUES (?,?,?,?,?)",
            (uid, req.username.lower(), req.name, hash_password(req.password), datetime.utcnow().isoformat())
        )
        conn.commit()
        token = make_token(uid, req.username.lower())
        return {"token": token, "name": req.name, "username": req.username.lower()}
    except sqlite3.IntegrityError:
        raise HTTPException(400, "Username sudah dipakai")
    finally:
        conn.close()

@app.post("/auth/login")
def login(req: LoginReq):
    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE username=? AND password=?",
        (req.username.lower(), hash_password(req.password))
    ).fetchone()
    conn.close()
    if not user:
        raise HTTPException(401, "Username atau password salah")
    token = make_token(user["id"], user["username"])
    return {"token": token, "name": user["name"], "username": user["username"]}

@app.get("/auth/me")
def me(user=Depends(get_current_user)):
    conn = get_db()
    u = conn.execute("SELECT name, username FROM users WHERE id=?", (user["sub"],)).fetchone()
    conn.close()
    if not u:
        raise HTTPException(404, "User tidak ditemukan")
    return {"name": u["name"], "username": u["username"]}

# ── SCHEDULE ROUTES ──
@app.get("/jadwal")
def get_schedules(user=Depends(get_current_user)):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM schedules WHERE user_id=? ORDER BY created DESC",
        (user["sub"],)
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        result.append({
            "id": r["id"],
            "subject": r["subject"],
            "book": r["book"] or "",
            "teacher": r["teacher"] or "",
            "time": r["time"] or "",
            "color": r["color"],
            "days": list(map(int, r["days"].split(",")))
        })
    return result

@app.post("/jadwal", status_code=201)
def add_schedule(req: ScheduleReq, user=Depends(get_current_user)):
    if not req.subject.strip():
        raise HTTPException(400, "Nama mata pelajaran wajib diisi")
    if not req.days:
        raise HTTPException(400, "Pilih minimal satu hari")
    
    conn = get_db()
    sid = req.id if req.id else str(uuid.uuid4())
    conn.execute(
        "INSERT OR REPLACE INTO schedules VALUES (?,?,?,?,?,?,?,?,?)",
        (sid, user["sub"], req.subject, req.book, req.teacher,
         req.time, req.color, ",".join(map(str, req.days)),
         datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()
    return {"id": sid, "subject": req.subject}

@app.delete("/jadwal/{schedule_id}")
def delete_schedule(schedule_id: str, user=Depends(get_current_user)):
    conn = get_db()
    result = conn.execute(
        "DELETE FROM schedules WHERE id=? AND user_id=?",
        (schedule_id, user["sub"])
    )
    conn.commit()
    conn.close()
    if result.rowcount == 0:
        raise HTTPException(404, "Jadwal tidak ditemukan")
    return {"deleted": schedule_id}

@app.get("/health")
def health():
    return {"status": "ok", "service": "BSS Backend"}
