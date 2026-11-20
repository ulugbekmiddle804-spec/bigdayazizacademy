# Online Test Platformasi

React + Django REST Framework + PostgreSQL + Redis + Celery asosida qurilgan, to'liq ishlaydigan
ikki bosqichli onlayn test tizimi. Bu loyihada foydalanuvchi qismi, admin panel, Excel eksport/import,
avtosaqlash, xavfsizlik choralari, Docker konfiguratsiyasi va yuklama testi bor.

---

## Imkoniyatlar

**Foydalanuvchi uchun**
- Ism, familiya, filial va fan tanlanadi. Hammasi to'ldirilgach «Testni boshlash» tugmasi chiqadi.
- 16 ta fan shu tartibda chiqadi: Ingliz tili, Rus tili, Arab tili, Koreys tili, Ona tili, Turk tili, Kimyo,
  Biologiya, Matematika, Mental arifmetika, IT (Frontend), IT (Backend), Hamshiralik, Boshlang'ich ta'lim,
  Tarix, Boshqa.
- 1–15-fanlar 2 bosqichli: 1-bosqich **Akademik test** (20 ta savol, 25 daqiqa, umumiy akademik bankdan),
  2-bosqich **Fan testi** (30 ta savol, 40 daqiqa, shu fanning o'zidan). Jami 50 ta savol.
  «Boshqa» fanida faqat 1-bosqich (Akademik test) bor. Soni, vaqti va manbaini admin o'zgartiradi.
- Savollar bazadan tasodifiy tanlanadi va aralashtiriladi, javob variantlari ham aralashtiriladi.
- Har bir bosqichda countdown taymer ishlaydi (5 va 1 daqiqa qolganda ogohlantiradi). Vaqt tugaganda bosqich
  avtomatik yakunlanadi.
- Oldingi/keyingi tugmalari, savollar navigatsiya paneli va progress bar bor. Klaviatura bilan ham ishlash
  mumkin: ← → savollar orasida, A–D yoki 1–4 javob tanlash.
- **Avtosaqlash:** har bir javob avval brauzerga (localStorage), keyin serverga yoziladi. Sahifa yangilansa ham
  javoblar yo'qolmaydi.
- **Internet uzilsa:** javoblar qurilmada saqlanadi, «Oflayn» belgisi ko'rinadi, ulanish tiklanishi bilan
  avtomatik yuboriladi. Tab yopilayotganda `keepalive` so'rov bilan yuboriladi.
- Yakunlashdan oldin tasdiqlash oynasi chiqadi. Unda bo'sh qolgan savollar soni va raqamlari ko'rinadi
  (raqamni bossangiz o'sha savolga o'tadi).
- Yakunda «Test muvaffaqiyatli topshirildi» sahifasi chiqadi. Ball va javoblar kaliti faqat admin ruxsat
  bergan bo'lsa ko'rsatiladi.

**Admin panel** (`/admin`)
- Boshqaruv paneli: jami, yakunlangan, hozir topshirayotganlar, o'rtacha natija, 14 kunlik grafik, fanlar va
  filiallar kesimidagi statistika. Savollar yetmay qolgan fanlar haqida ogohlantirish chiqadi.
- Natijalarda har bir kishi uchun **1-bosqich (Akademik) foizi, 2-bosqich (Fan testi) foizi va umumiy foiz**
  ko'rinadi (Excel eksportida ham).
- **O'chirish:** bitta natijani, belgilanganlarni yoki hammasini (filtr qo'yilgan bo'lsa, faqat filtrdagilarni)
  o'chirish mumkin. Hammasini o'chirishda «O'CHIRISH» so'zini yozib tasdiqlash kerak.
- Butun sayt iPhone va Android telefonlarga moslangan: telefonda natijalar kartochka ko'rinishida, oynalar
  pastdan chiqadi, test tugmalari doim barmoq ostida, iPhone'dagi «notch» va pastki chiziq hisobga olingan.
- Natijalar: ism va familiya bo'yicha qidiruv, filial, fan, holat va sana bo'yicha filter, ball, vaqt yoki
  familiya bo'yicha saralash, sahifalash.
- **Excel eksport**: oddiy ko'rinishda yoki har bir savol javobi bilan (ikkinchi varaq). Joriy filterlar
  eksportga ham qo'llanadi.
- Batafsil natija sahifasida quyidagilar bor:
  - boshlangan va tugagan vaqt, sarflangan vaqt;
  - 1- va 2-bosqich natijalari;
  - har bir savolda tanlangan javob va to'g'ri javob, to'g'ri/noto'g'ri/bo'sh filtrlari.
- Qayta topshirishga alohida ruxsat berish, natijani bekor qilish yoki o'chirish.
- Savollar: qo'shish, tahrirlash, o'chirish, faol/nofaol qilish. Qidiruv va filterlar bor. Har bir savolda
  2–6 variant bo'ladi va aynan bitta to'g'ri javob tanlanadi.
- **Savollarni Excel orqali import/eksport** qilish mumkin, shablon ham bor. Fayldagi barcha qatorlar oldin
  tekshiriladi va xatolik bo'lsa qator raqami bilan ko'rsatiladi. Fayl to'liq qabul qilinadi yoki hech
  narsa qo'shilmaydi.
- Fanlar va bosqichlar: fan, yo'nalish (guruh) va ikonka boshqariladi. Har bir bosqich uchun nom, savollar
  soni, vaqt, yoqish/o'chirish va **savollar manbai** (Akademik bank yoki fanning o'zi) sozlanadi.
  «Akademik test» banki ro'yxatda birinchi turadi va foydalanuvchiga alohida fan bo'lib ko'rinmaydi.
- **Word (.docx) orqali test biriktirish**: Fanlar → «Word orqali test» yoki Savollar → «Word orqali».
  Avval «Tekshirish» (fayl saqlanmaydi, savollar va xatolar ko'rsatiladi), keyin «Saqlash».
- Filiallarni boshqarish.
- Sozlamalar:
  - test topshirishni ochish/yopish;
  - ballni ko'rsatish;
  - javoblar kalitini ko'rsatish;
  - hamma uchun qayta topshirish.
- Zaxira sifatida Django admin ham bor: `/django-admin/`.

---

## Arxitektura

```
                ┌──────────────── Docker Compose ────────────────┐
 Brauzer ──►  nginx (frontend)  ──/api──►  Django + DRF (gunicorn gthread)
              React SPA (static)             │        │
                                             │        └──► Redis (kesh, throttle, Celery broker)
                                             └──► PostgreSQL (psycopg3 connection pool)
                                     Celery worker + beat ──► muddati o'tgan testlarni yopish
                └────────────────────────────────────────────────┘
```

```
backend/
  config/            settings, urls, celery
  apps/core/         sayt sozlamalari (singleton), throttling, validatsiya, health
  apps/catalog/      Branch, Subject, StageConfig, Question, Option + Redis kesh + demo ma'lumotlar
  apps/exams/        Attempt, AttemptStage, AttemptAnswer, test logikasi (services.py), API, Celery task
  apps/adminapi/     admin REST API, Excel eksport/import
frontend/
  src/pages/         Kirish, Test, Yakuniy sahifalar
  src/admin/         Admin panel (alohida yuklanadi - lazy loading)
  src/store/exam.ts  test holati (zustand + localStorage)
  src/lib/useAnswerSync.ts   ishonchli avtosaqlash mexanizmi
loadtest/simulate.py   yuklama testi va javoblar yaxlitligini tekshirish
```

---

## Tez ishga tushirish (Docker)

Talab: Docker va Docker Compose v2.

```bash
cp .env.example .env
# .env ichida DJANGO_SECRET_KEY, ADMIN_PASSWORD, POSTGRES_PASSWORD ni albatta o'zgartiring
docker compose up -d --build
```

- Sayt: http://localhost:8080
- Admin panel: http://localhost:8080/admin. Login va parol `.env` faylidagi `ADMIN_USERNAME` va
  `ADMIN_PASSWORD`.
- Django admin: http://localhost:8080/django-admin/

Birinchi ishga tushishda migratsiyalar avtomatik bajariladi. Bunda demo ma'lumotlar yuklanadi (6 ta filial,
8 ta yo'nalish, 480 ta savol) va admin foydalanuvchi yaratiladi. Demo ma'lumot kerak bo'lmasa
`SEED_DEMO=0` qiling.

Foydali buyruqlar:

```bash
docker compose logs -f backend
docker compose exec backend python manage.py createsuperuser        # qo'shimcha admin
docker compose exec backend python manage.py seed_demo --reset-questions   # demo savollarni qayta yuklash
docker compose exec backend python manage.py test apps              # backend testlari
```

### Server (production) uchun eslatmalar
- Domen nomini `DJANGO_ALLOWED_HOSTS` va `DJANGO_CSRF_TRUSTED_ORIGINS` ga yozing, masalan
  `https://test.example.uz`.
- HTTPS'ni (masalan Caddy, Traefik yoki tashqi nginx bilan) yoqib, `HTTPS=1` qiling. Shunda cookie'lar faqat
  HTTPS orqali yuboriladi va HSTS yoqiladi.
- `WEB_CONCURRENCY` qiymatini taxminan protsessor yadrolari soni × 2 qilib qo'ying. `DB_POOL_MAX ×
  WEB_CONCURRENCY` qiymati PostgreSQL'ning `max_connections` (200) dan kichik bo'lishi kerak.
- **CDN:** frontend build'ida `VITE_PUBLIC_BASE=https://cdn.example.com/` bersangiz, JS/CSS fayllar CDN'dan
  yuklanadi. Fayl nomlari hash'li, shuning uchun ular 1 yil keshlanadi. Django static fayllari uchun
  `STATIC_URL` ni CDN manziliga qo'yish mumkin.

---

## Internetga chiqarish (Railway + Cloudflare Pages)

Backend Railway'da, frontend Cloudflare Pages'da: qadamma-qadam yo'riqnoma [DEPLOY.md](DEPLOY.md) faylida.

## Lokal ishga tushirish (Dockersiz, SQLite bilan)

Kerak: Python 3.11+ va Node.js 20+. PostgreSQL va Redis kerak emas: `backend/.env.local` fayli SQLite'ni
yoqadi (baza `backend/db.sqlite3` ga yoziladi). Admin: `admin` / `admin12345` (shu faylda o'zgartiriladi).

**1-terminal, backend** (Windows):
```bat
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-local.txt
python manage.py migrate
python manage.py seed_demo
python manage.py ensure_admin
python manage.py runserver 8000
```
macOS / Linux'da faqat aktivlash boshqacha: `source .venv/bin/activate` (`python` o'rniga `python3`).

**2-terminal, frontend:**
```bash
cd frontend
npm install
npm run dev
```
Brauzerda: http://localhost:5173 (test), http://localhost:5173/admin (admin panel). `/api` so'rovlari
avtomatik 8000-portdagi backendga yuboriladi. Keyingi safar faqat `runserver` va `npm run dev` yetarli.
Bazani noldan boshlash uchun `db.sqlite3` faylini o'chirib, migrate/seed_demo/ensure_admin'ni qayta bajaring.

---

## Xavfsizlik

| Talab | Qanday bajarilgan |
|---|---|
| To'g'ri javoblar frontendga yuborilmaydi | Foydalanuvchiga savol matni va variantlar (`id`, `text`) beriladi, `is_correct` hech qachon yuborilmaydi. Variantlar tasodifiy UUID bilan belgilangan, shuning uchun id tartibidan to'g'ri javobni topib bo'lmaydi. Buni avtomatik test ham tekshiradi. |
| Javoblar kaliti faqat backendda | Test boshlanganda savol va kalit nusxasi (snapshot) serverda saqlanadi. Keyin admin savolni o'zgartirsa ham eski natijalar buzilmaydi. |
| Natijani foydalanuvchi o'zgartira olmaydi | Baholash faqat serverda, bosqich yakunlanganda bajariladi. Har bir test o'zining maxfiy tokeni bilan himoyalangan: bazada faqat SHA-256 xeshi saqlanadi. Boshqa testning savoliga javob yozib bo'lmaydi. |
| Vaqtni aldab bo'lmaydi | Muddat serverda saqlanadi. Muddatdan keyin kelgan javoblar qabul qilinmaydi (tarmoq kechikishi uchun 20 soniya qo'shimcha vaqt bor). Celery beat tashlab ketilgan testlarni avtomatik yopadi. |
| Admin API himoyasi | Session autentifikatsiya, faqat `is_staff` foydalanuvchilar, CSRF tekshiruvi. Login uchun alohida rate limit bor. |
| Parollar | Django PBKDF2-SHA256 (salt bilan) va murakkablik validatorlari. |
| SQL injection | Faqat Django ORM ishlatiladi (parametrlangan so'rovlar). |
| XSS | React matnni avtomatik ekranlaydi, `dangerouslySetInnerHTML` ishlatilmagan. Qattiq Content-Security-Policy, X-Frame-Options, nosniff sarlavhalari qo'yilgan. |
| Input validation | Ism va familiya faqat harflardan iborat bo'lishi, uzunligi 2–50 belgi. Barcha so'rovlar DRF serializer orqali tekshiriladi. Excel import qatorma-qator tekshiriladi. Eksportda `=` bilan boshlanadigan matn formula bo'lib qolmaydi. |
| Rate limiting | DRF throttling: test boshlash IP bo'yicha; javob saqlash har bir test tokeni bo'yicha, chunki bir sinfdagi o'quvchilar bitta IP'dan kirishi mumkin; admin login. Bundan tashqari nginx'da IP bo'yicha flood himoyasi bor. |
| Qayta topshirish | Bir kishi (ism + familiya + filial + fan) bir vaqtda faqat bitta faol testga ega bo'la oladi (bazada unique constraint). Yakunlangandan keyin qayta topshirish uchun admin ruxsati kerak, ruxsat bir marta ishlatiladi. Sozlamalarda hamma uchun ochish ham mumkin. |

---

## Tezlik va yuklama testi

Optimallashtirishlar:
- Savollar havzasi, filial va fanlar ro'yxati, sayt sozlamalari Redis'da keshlanadi. Kesh ma'lumot
  o'zgarganda versiya raqami orqali yangilanadi.
- PostgreSQL uchun psycopg3 connection pool ishlatiladi. Kerakli indekslar qo'yilgan. Ro'yxatlarda
  `select_related`/`prefetch_related` ishlatiladi. Natijalar jadvalida ball denormalizatsiya qilingan,
  shuning uchun saralash tez ishlaydi.
- Gunicorn `gthread` rejimida ishlaydi. Redis ishlamay qolsa ham sayt to'xtamaydi
  (`IGNORE_EXCEPTIONS`).
- Frontend sahifalari kod bo'yicha bo'lingan (lazy loading). Admin panel oddiy foydalanuvchiga
  yuklanmaydi; ilova kodi taxminan 9 KB (gzip).
- Faqat `transform`/`opacity` animatsiya qilinadi (GPU). Test paytida fon soddalashtiriladi.
  `prefers-reduced-motion` hisobga olingan.
- Avtosaqlashda o'zgarishlar 350 ms ichida guruhlab yuboriladi. Xatolikda qayta urinish oralig'i
  bosqichma-bosqich oshadi.

Yuklama testini o'zingiz ishga tushirish:

```bash
pip install httpx
python loadtest/simulate.py --base http://localhost:8080 --users 150 --admin-password 'ADMIN_PAROLI'
```

Har bir virtual foydalanuvchi testni boshidan oxirigacha topshiradi. Har bir javob alohida so'rov bilan
yuboriladi, ba'zan javob o'zgartiriladi va sahifa yangilanadi. Test oxirida skript admin API orqali har bir
javob serverda to'g'ri saqlanganini tekshiradi.

Natijalar 4 yadroli muhitda olingan. Barcha 6 ta konteyner bitta mashinada ishlagan va barcha so'rovlar
bitta IP'dan yuborilgan:

| Ssenariy | Foydalanuvchi | So'rovlar | Xatolar | Yo'qolgan javoblar |
|---|---|---|---|---|
| Ekstremal: 150 kishi bir vaqtda, javoblar orasida 0–0.3 s | 150 | 8 804 (245 so'rov/s) | 0 | 0 |
| Realistik: 300 kishi bir vaqtda, javoblar orasida 0–2 s | 300 | 17 536 (215 so'rov/s) | 0 | 0 |

Ikkala ssenariyda ham javob saqlash p50 ≈ 0.2–0.3 s, p95 ≈ 0.9 s. 300 kishi aynan bir soniyada
"Boshlash" tugmasini bossa, testni ochish 1–3 s oladi. To'liq natija: `loadtest/results/realistic-300.txt`. Haqiqiy imtihonda bir kishi har 20–60
soniyada bitta javob beradi, ya'ni yuklama bu testdagidan o'nlab marta kam bo'ladi.

---

## Savollarni Excel orqali import qilish

Admin panel → Savollar → Import → «Shablon». Ustunlar:

| Fan kodi | Bosqich | Savol | A | B | C | D | E | F | To'g'ri javob | Ball | Qiyinlik | Faol |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| math | 1 | 5 + 7 = ? | 12 | 11 | 13 | 10 | | | A | 1 | oson | ha |

Fan kodlari: `academic`, `english`, `russian`, `arabic`, `korean`, `uzbek`, `turkish`, `chemistry`, `biology`,
`math`, `mental`, `it-frontend`, `it-backend`, `nursing`, `primary`, `history`, `other`
(yangi fanlar kodini admin paneldan ko'rasiz). Eksport qilingan fayl ham xuddi shu formatda bo'ladi, shuning
uchun uni tahrirlab qayta import qilish mumkin.

---

## Testlarni Word orqali biriktirish

Format (o'qituvchilar ishlatadigan oddiy ko'rinish; «Namuna (Word)» tugmasi tayyor fayl beradi):

```
1. Savol matni (kod yoki matn parchasi keyingi qatorlarda bo'lishi mumkin)
A) variant
B) variant
C) variant
D) variant

JAVOBLAR KALITI
| 1 | 2 | 3 |      <- jadval (raqamlar qatori + harflar qatori) yoki matn: "1-A, 2-C"
| A | C | B |
```

- Variant harflari: A–F, kirill А–Е (а, б, в, г ham), ①–⑥, arab أ ب ج د.
- Kalit o'rniga to'g'ri variant oldiga `*` yoki `+` qo'yish mumkin: `*B) variant`.
- Fayl to'liq tekshiriladi: javobsiz savol, takroriy variant, kalitda ortiqcha raqam va h.k. bo'lsa savol raqami
  bilan ko'rsatiladi va hech narsa saqlanmaydi.
- «Mavjud savollar» bo'yicha: yangilarini qo'shish yoki shu fan va bosqichdagi eski savollarni almashtirish.
- Berilgan 15 ta haqiqiy fayl `backend/apps/adminapi/fixtures/` papkasida turibdi va avtomatik testda tekshiriladi.

## Boshlang'ich savollar bazasi

`python manage.py seed_demo` (Docker'da avtomatik) 470 ta savol yuklaydi: Akademik bank 20 ta (akademiya reglamenti), har bir fan aniq 30 ta qiyinroq savol. To‘g‘ri javob variantlar ichida uzunligi bilan ajralib turmaydi (buni `apps/catalog/tests.py` tekshiradi), to‘g‘ri javob harfi esa har bir ishtirokchi uchun A/B/C/D bo‘ylab teng taqsimlanadi va ketma-ket ikki savolda bir xil harf bo‘lmaydi (`apps/catalog/answer_order.py`). Eski bazani yangilash: `python manage.py seed_demo --reset-questions`. Har bir fan
35–111 ta. Berilgan fayllardagi savollar (tuzatishlar bilan) va ular asosida tuzilgan qiyinroq savollar
`backend/apps/catalog/demo_data/` ichida.

---

## Testlar

```bash
cd backend && python manage.py test apps    # 39 ta test: test oqimi, baholash, vaqt, qayta topshirish,
                                            # xavfsizlik, admin API, CSRF, Excel va Word import
cd frontend && npm run typecheck && npm run build
```

## Muhit o'zgaruvchilari

Barchasi izohlari bilan `.env.example` faylida berilgan.
