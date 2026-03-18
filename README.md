# BSS Backend

FastAPI + SQLite backend untuk Bendahara Safety System.

## Deploy ke Railway (GRATIS)

1. Buka https://railway.app → Sign up pakai GitHub
2. Klik "New Project" → "Deploy from GitHub repo"
3. Push folder ini ke GitHub dulu, lalu pilih repo-nya
4. Railway otomatis detect Python + install dependencies
5. Di tab "Variables", tambahkan:
   - `JWT_SECRET` = (string random panjang, bebas)
6. Setelah deploy, copy URL-nya (contoh: https://bss-backend-xxx.up.railway.app)
7. Paste URL itu ke file jadwal.html bagian `const API_URL = "..."`

## Test API (pakai browser)
Buka: https://URL-KAMU.up.railway.app/docs
→ Swagger UI otomatis tersedia untuk test semua endpoint
