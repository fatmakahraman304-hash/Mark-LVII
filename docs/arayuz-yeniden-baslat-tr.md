# JARVIS arayüz düzeni ve güncelleme sonrası yeniden başlatma

## Arayüz yerleşimi

- **Sol üst:** Ayarlar (dişli), Kontroller (kaydırıcı), **GÜNCELLE** ve tam ekran.
- **Sağ üst:** Saat ve tarih.
- **Sol sütun (eski halinde):** SYSTEMS, NETWORK, STATUS, görevler ve konum bölümü.
- **Orta:** JARVIS HUD; dinliyor/konuşuyor durumu burada kalır.
- **Sağ sütun (eski halinde):** COMMUNICATIONS (sohbet geçmişi), COMMAND
  (metin komutu, dosya seçimi, mikrofon ve konuşmayı durdurma).

**Yalnızca üst kısımdaki düğmeler** sola taşındı. Yan sütunlar kullanıcı
isteği doğrultusunda önceki konumlarına geri getirildi.

Sol üstteki ikinci `LISTENING` etiketi kaldırıldı. Dinleme durumu,
sistem mikrofon durumu ve orta HUD'da gösterilmeye devam eder. Menülerin
üstteki düğme ile açılma ve kapanma davranışı korunur.

## Güncelleme düğmesi

`GÜNCELLE` başarılı bir güncelleme uyguladığında arayüz kısa bir
bilgilendirmeden sonra **kendiliğinden kapanıp yeniden açılmak üzere**
yeniden başlatma işlemini planlar. Bu davranış zaten mevcuttu; yeni
`core/restart_manager.py` aracılığıyla daha güvenli hale getirildi.

Normal başlatma:
1. `tools/restart_app.py` bağımsız yardımcı süreç olarak açılır.
2. JARVIS mevcut Qt/konuşma oturumunu kapatır.
3. Yardımcı, önceki sürecin kapanmasını bekler ve yeni `main.py`
   sürecini aynı Python ortamıyla başlatır.

Yerel OSIRIS yöneticisi üzerinden başlatıldığında:
1. JARVIS yeniden başlatma işaretiyle kapanır (çıkış kodu 75).
2. `tools/start_with_osiris.py` JARVIS'i aynı OSIRIS oturumunda yeniden
   açar; ikinci bir bağımsız JARVIS örneği başlatılmaz.

Yardımcı çalıştırılamazsa JARVIS kendiliğinden kapanmaz; ekranda hata
gösterilir ve elle kapatıp açmak gerektiği açıklanır.

**Sınır:** Güncelleme Python bağımlılıklarının değişmesini gerektiriyorsa
güncelleyici dosyalara dokunmadan durur; önce bağımlılıklar kurulmalıdır.
Hiç yeni sürüm yoksa yeniden başlatma yapılmaz.

## Doğrulama

CI testleri, otomatik restart planlaması ve yerleşim kodunu Windows ve
Linux üzerinde doğrular. Gerçek Windows ekranında ölçeklendirme, menü
konumları ve mikrofon/OSIRIS ile birlikte yeniden başlatma ayrıca
kontrol edilmelidir.
