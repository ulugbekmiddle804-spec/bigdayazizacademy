"""NOT LOADED (kept for reference): the earlier general academic questions, replaced on 2026-11-21 by the
academy regulations test the person supplied (see academic.py).

Academic test bank (stage 1 for every subject): logic and numeracy, pedagogy and
psychology, professional ethics. Items: (text, correct option, wrong options...).
"""

ORIGINAL = []

EXTRA = [
    # --- Mantiqiy fikrlash va matematik savodxonlik
    ("Ketma-ketlikni davom ettiring: 2, 6, 12, 20, 30, ?", "42", "40", "44", "36"),
    ("Ketma-ketlikni davom ettiring: 3, 5, 9, 17, 33, ?", "65", "49", "64", "66"),
    ("«Barcha o‘qituvchilar — pedagog. Ba’zi pedagoglar — psixolog.» Shu ikki fikrdan qaysi xulosa mantiqan "
     "albatta kelib chiqadi?",
     "O‘qituvchilarning psixolog ekanligi haqida aniq xulosa chiqarib bo‘lmaydi",
     "Ba’zi o‘qituvchilar — psixolog", "Barcha psixologlar — o‘qituvchi", "Hech bir o‘qituvchi psixolog emas"),
    ("«Hamma A — B. Hech bir B — C emas.» Qaysi xulosa albatta to‘g‘ri?",
     "Hech bir A — C emas", "Ba’zi A — C", "Hamma C — A", "Ba’zi C — B"),
    ("«Yomg‘ir yog‘sa, yo‘l ho‘l bo‘ladi» degan fikr rost. Quyidagilardan qaysi biri ham albatta rost?",
     "Yo‘l ho‘l bo‘lmasa, yomg‘ir yog‘magan", "Yo‘l ho‘l bo‘lsa, yomg‘ir yoqqan",
     "Yomg‘ir yog‘masa, yo‘l quruq bo‘ladi", "Yo‘l faqat yomg‘irdan ho‘l bo‘ladi"),
    ("Sinfda 30 o‘quvchi bor. 18 tasi ingliz tili, 15 tasi rus tili to‘garagiga qatnashadi, 5 tasi hech "
     "birida qatnashmaydi. Ikkala to‘garakka qatnashadiganlar nechta?", "8", "3", "5", "10"),
    ("Mahsulot narxi avval 20% ga oshirildi, so‘ng yangi narx 20% ga kamaytirildi. Yakuniy narx dastlabki "
     "narxga nisbatan qanday o‘zgardi?", "4% ga kamaydi", "O‘zgarmadi", "4% ga oshdi", "2% ga kamaydi"),
    ("Soat 3:40 ni ko‘rsatganda soat va minut millari orasidagi kichik burchak necha gradus?",
     "130°", "120°", "140°", "125°"),
    ("Ota o‘g‘lidan 4 marta katta. 20 yildan keyin ota o‘g‘lidan 2 marta katta bo‘ladi. Otaning hozirgi yoshi "
     "nechada?", "40", "36", "44", "48"),
    ("Har bir harfni lotin alifbosida o‘zidan keyingi harf bilan almashtirib, KITOB so‘zi LJUPC deb yozildi. "
     "Shu qoida bilan DARS so‘zi qanday yoziladi?", "EBST", "EBSU", "ECST", "CZQR"),
    ("Uch ishchi birgalikda ishni 4 kunda bajaradi. Birinchisi yolg‘iz 12 kunda, ikkinchisi yolg‘iz 18 kunda "
     "bajaradi. Uchinchisi yolg‘iz necha kunda bajaradi?", "9", "6", "8", "12"),
    ("Besh o‘quvchining ballari: 90, 50, 100, 60, 90. O‘rta arifmetik qiymat va mediana mos ravishda qaysi "
     "javobda?", "78 va 90", "90 va 78", "78 va 100", "80 va 90"),
    ("Kub shaklidagi yog‘ochning barcha sirti bo‘yaldi, so‘ng u 27 ta teng kichik kubchaga kesildi. Nechta "
     "kubchaning faqat bitta yog‘i bo‘yalgan?", "6", "8", "12", "1"),
    ("Besh kishi navbatda turibdi. D birinchi, E eng oxirida. A B dan oldinda, B esa C dan oldinda turibdi. "
     "Navbatda uchinchi kim?", "B", "A", "C", "E"),
    ("Avtomobil 2 soat 60 km/soat, so‘ng 1 soat 90 km/soat tezlikda yurdi. Butun yo‘ldagi o‘rtacha tezlik "
     "qancha?", "70 km/soat", "75 km/soat", "72 km/soat", "65 km/soat"),
    ("5 ta stanok 5 daqiqada 5 ta detal tayyorlaydi. 100 ta stanok 100 ta detalni necha daqiqada tayyorlaydi?",
     "5", "100", "20", "1"),
    ("Ikki sonning yig‘indisi 50 ga, ayirmasi 14 ga teng. Kattasini toping.", "32", "36", "30", "28"),
    ("Kitob : kutubxona = rasm : ?", "Muzey (galereya)", "Rassom", "Mo‘yqalam", "Ramka"),
    ("Qaysi shakl qolganlaridan mantiqan farq qiladi?", "Doira", "Romb", "Trapetsiya", "Kvadrat"),
    ("Sinfdagi o‘g‘il bolalar qizlardan 25% ko‘p. Qizlar o‘g‘il bolalardan necha foiz kam?",
     "20%", "25%", "15%", "30%"),
    ("Qutida 3 ta qizil va 5 ta ko‘k shar bor. Tavakkaliga 2 ta shar olinsa, ikkalasi ham ko‘k bo‘lish "
     "ehtimoli qancha?", "5/14", "25/64", "5/8", "3/14"),
    ("200 o‘quvchidan 40% i matematikani, 25% i ingliz tilini, qolganlari boshqa fanlarni tanladi. Boshqa "
     "fanlarni tanlaganlar nechta?", "70", "65", "75", "80"),
    ("1 dan 100 gacha bo‘lgan sonlardan nechtasi 3 ga ham, 5 ga ham bo‘linmaydi?", "53", "47", "60", "54"),
    # --- Pedagogika va psixologiya
    ("Quyidagilardan qaysi biri ichki motivatsiyaga misol bo‘ladi?",
     "O‘quvchi mavzu qiziqarli bo‘lgani uchun qo‘shimcha adabiyot o‘qiydi",
     "O‘quvchi yaxshi baho olish uchun o‘qiydi",
     "O‘quvchi ota-onasi sovg‘a va’da qilgani uchun o‘qiydi",
     "O‘quvchi jazodan qo‘rqib uy vazifasini bajaradi"),
    ("L. S. Vygotskiyning «yaqin rivojlanish zonasi» tushunchasi nimani anglatadi?",
     "Bola mustaqil bajara oladigan va kattalar yordamida bajara oladigan vazifalar orasidagi oraliqni",
     "Bola allaqachon mustaqil bajara oladigan vazifalar doirasini",
     "Bolaning yoshiga xos jismoniy rivojlanish chegarasini",
     "Bola hech qanday yordam bilan ham bajara olmaydigan vazifalarni"),
    ("J. Piaget nazariyasiga ko‘ra konkret operatsiyalar bosqichi (taxminan 7–11 yosh) uchun nima xos?",
     "Saqlanish (konservatsiya) tushunchasi shakllanadi, ammo mavhum fikrlash hali cheklangan",
     "Gipotetik-deduktiv, to‘liq mavhum fikrlash",
     "Dunyoni faqat sezgi va harakatlar orqali bilish",
     "Ramziy o‘yin va egotsentrizmning eng kuchli namoyon bo‘lishi"),
    ("Blum taksonomiyasining qayta ko‘rilgan (Anderson–Krathwohl) talqinida eng yuqori bosqich qaysi?",
     "Yaratish", "Baholash", "Tahlil qilish", "Qo‘llash"),
    ("G. Gardnerning ko‘p intellekt nazariyasiga ko‘ra, musiqani yaxshi his qiladigan, ammo matematikada "
     "qiynaladigan o‘quvchi haqida qaysi xulosa to‘g‘ri?",
     "Uning musiqiy intellekti kuchli; o‘qitishda shu kuchli tomondan foydalanish mumkin",
     "Uning umumiy intellekt darajasi past",
     "U faqat musiqa maktabida o‘qishi kerak",
     "Intellekt yagona va o‘zgarmas, shuning uchun unga yordam berib bo‘lmaydi"),
    ("Ya. A. Komenskiy «Buyuk didaktika» asarida qaysi ta’lim tizimini asoslab bergan?",
     "Sinf-dars tizimi", "Bell-Lankaster tizimi", "Dalton-plan", "Brigada-laboratoriya usuli"),
    ("Formativ va summativ baholashning asosiy farqi nimada?",
     "Formativ baholash o‘qitish jarayonida uni yaxshilash uchun, summativ esa bosqich yakunida natijani "
     "qayd etish uchun o‘tkaziladi",
     "Formativ baholash faqat yozma, summativ faqat og‘zaki bo‘ladi",
     "Formativ baholash faqat yil oxirida o‘tkaziladi",
     "Ular o‘rtasida farq yo‘q, ikkalasi ham faqat baho qo‘yish uchun"),
    ("Test sinovining ishonchliligi (reliability) nimani bildiradi?",
     "Takroriy o‘lchashlarda natijalarning barqaror chiqishini",
     "Test o‘lchashi kerak bo‘lgan narsani o‘lchashini",
     "Test savollarining qiyinlik darajasini",
     "Testni o‘tkazish arzonligini"),
    ("Darsni tez-tez buzadigan o‘quvchiga nisbatan eng samarali dastlabki yondashuv qaysi?",
     "Xulq sababini aniqlash, aniq qoidalar o‘rnatish va ijobiy xatti-harakatni rag‘batlantirish",
     "Uni darsdan chiqarib yuborish",
     "Butun sinfni jazolash",
     "E’tiborsiz qoldirib, hech qanday chora ko‘rmaslik"),
    ("«Teskari sinf» (flipped classroom) modelining mohiyati nimada?",
     "Yangi material bilan uyda tanishiladi, darsda esa amaliy topshiriq va muhokama qilinadi",
     "Dars faqat sinfdan tashqarida, o‘qituvchisiz o‘tkaziladi",
     "O‘quvchilar o‘qituvchi o‘rniga baho qo‘yadi",
     "Darslar teskari tartibda: avval nazorat, keyin mavzu"),
    ("Inklyuziv ta’lim nima?",
     "Alohida ta’lim ehtiyojlari bo‘lgan bolalarning umumiy ta’lim muassasasida tengdoshlari bilan birga "
     "o‘qishini ta’minlash",
     "Alohida ehtiyojli bolalarni faqat maxsus maktablarda o‘qitish",
     "Faqat iqtidorli bolalar uchun alohida sinflar ochish",
     "Barcha o‘quvchilarni faqat masofadan o‘qitish"),
    ("Kognitiv yuklama nazariyasiga (J. Sweller) ko‘ra yangi va murakkab mavzuni o‘rgatishda nima tavsiya "
     "etiladi?",
     "Materialni kichik qismlarga bo‘lib, ishlangan namunalar bilan berish",
     "Barcha ma’lumotni bir vaqtda turli manbalardan berish",
     "Boshlovchilarga darhol yordamsiz mustaqil izlanish topshirig‘ini berish",
     "Slaydga matnni to‘liq yozib, uni ovoz chiqarib o‘qib berish"),
    ("H. Ebbinghausning unutish egri chizig‘idan o‘qitish uchun qanday amaliy xulosa chiqadi?",
     "Takrorlashni vaqt oraliqlari bilan taqsimlash bilimni uzoqroq saqlaydi",
     "Materialni bir kunda ko‘p marta yodlash yetarli, keyin takrorlash shart emas",
     "Unutish tezligi o‘qitish usuliga bog‘liq emas",
     "Yangi bilim takrorlanmasa ham yillar davomida saqlanadi"),
    ("Qaysi dars maqsadi SMART talablariga eng mos keladi?",
     "Dars oxirida o‘quvchilar 10 ta yangi so‘zdan kamida 8 tasini gapda to‘g‘ri qo‘llay oladi",
     "O‘quvchilar ingliz tilini yaxshi biladi",
     "O‘quvchilar mavzuni tushunadi",
     "O‘quvchilar darsga qiziqish bilan qatnashadi"),
    ("Evristik (Sokrat) suhbati metodining mohiyati nimada?",
     "O‘qituvchi savollar zanjiri orqali o‘quvchini mustaqil xulosaga olib keladi",
     "O‘qituvchi tayyor xulosani aytib, o‘quvchilar uni yozib oladi",
     "O‘quvchilar savollarga faqat «ha» yoki «yo‘q» deb javob beradi",
     "Dars faqat matn o‘qish bilan o‘tadi"),
    ("Pedagogik refleksiya deganda nima tushuniladi?",
     "O‘qituvchining o‘z faoliyatini tahlil qilib, xulosa chiqarishi va uni takomillashtirishi",
     "O‘quvchilarning bir-birini baholashi",
     "Darsda ko‘rgazmali vositalardan foydalanish",
     "Dars rejasini boshqa o‘qituvchidan ko‘chirib olish"),
    ("Faol tinglashning (active listening) belgisi qaysi?",
     "Suhbatdosh fikrini o‘z so‘zlari bilan qayta ifodalash va aniqlashtiruvchi savollar berish",
     "Suhbatdoshning gapini bo‘lib, darhol maslahat berish",
     "Tinglash davomida boshqa ish bilan shug‘ullanish",
     "Faqat o‘z fikrini isbotlashga urinish"),
    # --- Kasbiy etika va ta’lim qonunchiligi
    ("O‘zbekiston Respublikasining amaldagi «Ta’lim to‘g‘risida»gi Qonuni qachon qabul qilingan (imzolangan)?",
     "2020-yil 23-sentabr", "1997-yil 29-avgust", "1992-yil 8-dekabr", "2017-yil 7-fevral"),
    ("O‘quvchining sog‘lig‘i yoki oilaviy ahvoli haqidagi maxfiy ma’lumotga nisbatan o‘qituvchi qanday yo‘l "
     "tutishi kerak?",
     "Faqat qonuniy va pedagogik zarurat bo‘lganda vakolatli shaxslarga ma’lum qiladi",
     "Boshqa ota-onalarga ogohlantirish sifatida aytib beradi",
     "Sinf oldida muhokama qiladi",
     "Ijtimoiy tarmoqdagi sinf guruhida e’lon qiladi"),
]
