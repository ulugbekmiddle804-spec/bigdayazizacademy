# Internetga chiqarish: backend → Railway, frontend → Cloudflare Pages

Qanday ishlaydi:

```
Brauzer ──► https://<loyiha>.pages.dev   (Cloudflare Pages: sayt fayllari)
                 │  /api/* so'rovlari
                 ▼
            frontend/functions/api/[[path]].ts   (Cloudflare'dagi kichik proksi)
                 │
                 ▼
            https://<servis>.up.railway.app      (Railway: Django + PostgreSQL)
```

Foydalanuvchi faqat Cloudflare manzilini ko'radi. `/api` so'rovlarini Cloudflare o'zi Railway'ga uzatadi,
shuning uchun admin panelga kirish (cookie) iPhone Safari'da ham muammosiz ishlaydi, CORS sozlash shart emas.

Ikkala xizmat ham kodni GitHub'dan oladi. Avval loyihani GitHub'ga yuklang (pastda GitHub'siz usul ham bor).

Tasodifiy kalitlar yasash uchun (Windows PowerShell):
```powershell
-join ((48..57)+(65..90)+(97..122) | Get-Random -Count 50 | % {[char]$_})
```

---

## 1. Railway (backend)

1. https://railway.com → **New Project** → **Deploy from GitHub repo** → repozitoriyni tanlang.
2. Servis → **Settings**:
   - **Root Directory:** `backend`
   - **Config file path:** `/backend/railway.json`. Bu fayl Dockerfile va health check'ni sozlaydi.
3. Loyihada **+ New → Database → PostgreSQL** qo'shing.
4. *(Tavsiya etiladi)* **+ New → Database → Redis** qo'shing. Bu kesh uchun: admin panelda qilingan o'zgarishlar hamma joyda darhol ko'rinadi.
5. Backend servis → **Variables** bo'limiga quyidagilarni kiriting:

   | O'zgaruvchi | Qiymat |
   |---|---|
   | `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` |
   | `REDIS_URL` | `${{Redis.REDIS_URL}}` (Redis qo'shilgan bo'lsa) |
   | `DJANGO_SECRET_KEY` | 50 belgili tasodifiy kalit |
   | `DJANGO_DEBUG` | `0` |
   | `HTTPS` | `1` |
   | `FRONTEND_URL` | `https://<loyiha>.pages.dev` (2-bo'limdan keyin aniq bo'ladi; o'z domeningiz ham bo'lsa, vergul bilan qo'shing) |
   | `PROXY_SECRET` | tasodifiy kalit; Cloudflare'da ham aynan shu qiymat bo'ladi |
   | `ADMIN_USERNAME` | `admin` |
   | `ADMIN_PASSWORD` | kuchli parol (kamida 8 belgi) |
   | `WEB_CONCURRENCY` | `3` |
   | `EXPIRED_SWEEP_IN_WEB` | `1` (vaqti tugagan testlarni har daqiqada yopadi, Celery kerak emas) |

6. **Settings → Networking → Generate Domain** tugmasini bosing. Natijada `https://<servis>.up.railway.app` manzili hosil bo'ladi.
7. Tekshiring: `https://<servis>.up.railway.app/api/health/` manzili `{"ok": true, ...}` qaytarishi kerak.

Har deploy'da migratsiyalar, savollar banki (`seed_demo`) va admin avtomatik tayyorlanadi.
Bu qadamlar `entrypoint.sh` ichida bajariladi.

## 2. Cloudflare Pages (frontend)

1. https://dash.cloudflare.com → **Workers & Pages → Create → Pages → Connect to Git** → repozitoriyni tanlang.
2. Build sozlamalari:
   - **Framework preset:** `None` (yoki `Vite`)
   - **Build command:** `npm run build`
   - **Build output directory:** `dist`
   - **Root directory:** `frontend`
3. **Environment variables (Production)** bo'limiga quyidagilarni kiriting:
   - `BACKEND_URL` = `https://<servis>.up.railway.app`
   - `PROXY_SECRET` = Railway'dagi bilan bir xil
4. **Save and Deploy** tugmasini bosing. Natijada `https://<loyiha>.pages.dev` manzili hosil bo'ladi.
5. Shu manzilni Railway'dagi `FRONTEND_URL` ga yozing. Railway o'zi qayta deploy qiladi.
6. *(Ixtiyoriy)* O'z domeningizni ulash: Pages → **Custom domains**. Bu domenni ham `FRONTEND_URL` ga vergul bilan qo'shing.

Admin panel: `https://<loyiha>.pages.dev/admin`

## GitHub'siz usul

Bu usulda ikkala servis ham buyruq orqali kompyuterdan yuklanadi.

```powershell
# Railway: loyiha va baza yuqoridagidek, sayt orqali yaratiladi
npm.cmd i -g @railway/cli
railway login
cd backend
railway link
railway up

# Cloudflare Pages
cd ..\frontend
npm.cmd install
npm.cmd run build
npx.cmd wrangler pages deploy dist --project-name aziz-academy-test
```

`wrangler pages deploy` buyrug'ini `frontend` papkasidan ishga tushiring. Shunda `functions/` papkasidagi `/api` proksi ham birga yuklanadi.
`BACKEND_URL` va `PROXY_SECRET` o'zgaruvchilari Pages → Settings → Variables bo'limida kiritiladi.

## Muammo bo'lsa

- **Saytda "BACKEND_URL sozlanmagan" xabari chiqadi.** Cloudflare'da `BACKEND_URL` kiritilmagan. Uni kiriting va qayta deploy qiling.
- **Admin panelga kirganda yoki fayl yuklashda "CSRF" xatosi chiqadi.** Railway'dagi `FRONTEND_URL` saytning aniq manziliga teng emas: `https://...`, oxirida `/` belgisiz bo'lishi kerak.
- **Railway health check o'tmayapti.** Servis loglarini oching. Ko'pincha sabab `DATABASE_URL` yoki `DJANGO_SECRET_KEY` kiritilmagani bo'ladi.
