# JARVIS — Nihai Seviye Teknik Yol Haritası

**Proje:** fatmakahraman304-hash/Mark-LVII (FatihMakes MARK LVII çatallaması)  
**Amaç:** Sesli, görsel, güvenli ve güvenilir kişisel asistan + OSIRIS Dünya
Komuta Merkezi. Gerçek olmayan bilimkurgu yetenekleri sunulmayacak.

## Ürün ilkeleri

1. **Gerçek yetenek:** Her araç sonucunda `done`, `unverified`, `failed` ayrımı.
2. **İzinli kontrol:** Silme, ödeme, mesaj gönderme, sistem ayarı, kamera ve
   benzeri yüksek etkili eylemler için kullanıcı onayı; ses modeli kendini onaylayamaz.
3. **Kaynaklı bilgi:** Her veri katmanında API kaynağı, son güncelleme,
   gecikme/önbellek ve eksiklik bilgisi görünür.
4. **Öncelikle yerel:** Anahtarlar hiçbir zaman depoya girmez; mümkünse yerel
   işleme, sıkı yerel arayüz/servis sınırları, bağlantı koptuğunda anlaşılır hata.
5. **Modülerlik:** Ses/LLM, OSIRIS, görev ajanları, hafıza ve UI ayrı modüllerdir.
6. **Performans:** Konuşma ve mikrofon asla harita veya araştırma API'si için
   bloklanmaz; işe özel zaman ve çağrı bütçeleri tanımlanır.
7. **Sahiplik/lisans:** Orijinal MARK LVII kodu CC BY-NC 4.0 altında kalır;
   OSIRIS MIT'dir. Kaynak ve atıflar korunur. Ticari yeniden lisanslama
   otomatik olarak mümkün değildir.

## Aşama 1 — OSIRIS köprüsü (başlandı)

- [x] Ayrı geliştirme dalı ve taslak PR
- [x] Sesli komutla OSIRIS katman URL'si oluşturma
- [x] Qt ana iş parçacığında isteğe bağlı gömülü harita penceresi
- [x] Eksik QtWebEngine için sistem tarayıcısı alternatifi
- [x] Açık kaynaklı OSIRIS istatistik/deprem API'lerini yalnızca okuma
- [x] Veri kaynağı, zaman damgası ve veri kesinliği açıklaması
- [x] İnternet bağımlılığı olmayan, mock'lanmış otomatik testler
- [ ] MARK LVII mikrofonu ve GUI'si üzerinde gerçek Windows uçtan uca test
- [ ] Testleri geçen, güvenli ana dal birleştirmesi

**Aşama bitiş kriteri:** "Dünya haritasını aç / depremleri göster / son
depremleri özetle" komutları Windows'ta çalışır; JARVIS konuşması çalışmaya
devam eder. Her başarısızlık gözlemlenebilir ve kullanıcıyı yanıltmaz.

## Aşama 2 — Yerel OSIRIS servisi

- OSIRIS kaynak kodunu ana JARVIS deposuna kopyalamadan ayrı paket/depo
  olarak kur; sürümü sabitle, lisans ve güncelleme notlarını sakla.
- Node sürümünü doğrula; tek tık/tek komut kurulum, yerel port/sürüm kontrolü,
  çökme sonrası temiz geri başlatma, isteğe bağlı otomatik açılış.
- Sunucu loopback'e bağlansın; ağdan dışarı açılmasın. RECON tarama, SDK
  ingest ve diğer mutasyon uçları varsayılan olarak kapalı.
- Sunucu kapanırsa JARVIS kapanmasın. Bağlantı ve yüklenme durumları
  `bağlanıyor/hazır/veri gecikmeli/hata` olarak gösterilsin.
- OSIRIS ile istemci arasında sürüm uyumu ve deprecation testleri.

**Bitiş kriteri:** Kullanıcı anahtar girmeden kaynakları destekleyen yerel
OSIRIS arayüzü açılıyor, kapatılabiliyor ve güvenli güncelleniyor.

## Aşama 3 — Etkileşimli 3D kontrol ve analitik

- İzinli yerel origin'e bağlı, imzalı/oturumlu ve sınırlandırılmış komut köprüsü;
  rastgele web sayfası bu köprüye erişemez.
- Katman aç/kapat, konum/ülke ara, yaklaştır, görünüm hazır ayarlarını uygula;
  bunları sayfayı yeniden yüklemeden yap (yerel OSIRIS entegrasyonu).
- Görünen harita durumunun JARVIS'e güvenli özeti; açık data API'lerinden
  gelen olaylar için kaynak/capture timestamp ve uygun önbellek.
- Kaynaklar eksikse veya eskiyse JARVIS canlıymış gibi konuşmasın.
- Kamusal yayın kameraları için hak/sözleşme, erişim ve performans kontrolleri.
- Kişi/özel kamera izlemesi, hassas hedef takibi veya askeri operasyonel
  yönlendirme sağlanmaz.

**Bitiş kriteri:** Sesli komutla aynı pencerede harita anında değişir, durum
bildirimi ile hangi değişikliğin doğrulandığı anlaşılır.

## Aşama 4 — Kişisel JARVIS'i güçlendirme

- Sesli konuşma: Türkçe, kesme/konuşmayı durdurma, yankı önleme, mikrofon testi,
  cihaz değiştirme, uzun görüşmeler, düşük gecikme.
- Akıllı araç yönlendirme: önce güvenilir veri, sonra yorum; tutarlı izin kapısı
  ve yüksek etkili eylemler için geri alma/denetim kaydı.
- Hafıza: silme/düzenleme, hassas veriyi ayırma, kaynak takibi,
  şifreleme/yedek/geri yükleme, onaylı uzun süreli kayıt.
- Araştırma ajanları: kaynak okuma, atıf doğrulama, adım bütçesi, kullanıcı
  tarafından durdurma, tekrar başlamada checkpoint.
- İsteğe bağlı ekran farkındalığı; kamera ekranına/tara-yıcıya izinsiz erişim yok.
- Donanım telemetrisi, cihazların mevcut durumu ve yanlış başarı bildirimlerini
  önleyen doğrulama.
- Önceden desteklenen bilgisayar kontrolü, kişisel ajan ve otomasyon
  özellikleri arasında tek bir izin/denetim katmanı.

## Aşama 5 — Dağıtım ve sürüm güvencesi

- Windows paketleme ve imzalı sürümler; bağımlılık kilitleme,
  başlangıç sihirbazı, health-check.
- Bilinen çalışma donanımları için ölçülmüş CPU, RAM, GPU ve ses gecikmesi.
- 20+ senaryo: GUI açılışı, mikrofon, QtWebEngine, OSIRIS yerel/çevrimiçi,
  API kapalı, ağ koptu, tarayıcı yok, model kota doldu, izin iptali, geri alma.
- CI: sözdizimi/birim/entegrasyon; gerçek Windows GUI testi,
  regresyon ve geri dönüş planı.
- Kullanıcı kılavuzu, özellik matrisi (çalışıyor/kısmen/planlı), hata raporu.
- Yalnızca kanıtlanan testler yeşil; başarısız testler kapatılmaz veya
  başarılı gibi gösterilmez.

## Şimdiki gerçek durum — 14 Kasım 2026

Geliştirme dalı: feature/osiris-world-command. Ana daldaki kişisel arayüz,
şehir haritası ve alt köşe yazısı değişikliği bu dalda korundu.

| Özellik | Mevcut kanıt | Tamamlanma kapısı |
|---|---|---|
| Sesli araç yönlendirme | Python birim testleri | Windows mikrofonundan gerçek araç çağrısı |
| Yeniden yüklemeden kontrol | JavaScript durum testleri ve QtWebEngine yerel test sayfası | Gerçek OSIRIS küresinde katman, şehir, zoom; belge yükleme sayısı 1 |
| Yerel servis | Sabit kaynak, üretim derlemesi, loopback başlangıç/sağlık kontrolü | Windows temiz kurulum, port dolu, çökme ve kapanma |
| Komut sonucu | done/failed/unverified; origin, parametre ve gecikme testleri | Windows sesli kullanımda sonuç bildirimi |
| Arayüz ve şehir haritası | Ana dal tasarımı korundu; regresyon testleri | Windows ekranında son görsel kontrol |
| Nihai dağıtım | Tamamlanmadı | Gerçek ses/cihaz, uzun görüşme, paketleme ve geri dönüş |

Yerel test sayfası gerçek WebGL küresinin yerine geçmez. Başlangıç sağlık
kontrolü bütün veri kaynaklarının hazır olduğunu göstermez. Aşama 1–3 tamamen
bitmiş sayılmaz.

Ana dal kabulü: Gerçek Windows ses/ekran kabulü ve kalan yerel servis
senaryoları doğrulanmadan bu geliştirme ana dala aktarılmaz.

## Bu geliştirmedeki test kaydı

- Python: 12 araç yönlendirme, 8 veri okuma, 5 servis yaşam döngüsü,
  4 şehir haritası ve 2 gerçek QtWebEngine taşıma/URL testi geçti.
- Node: 7 köprü sözleşmesi testi geçti.
- Sabitlenmiş gerçek OSIRIS üretim derlemesi geçti; upstream dinamik
  dosya tarama uyarıları mevcut, bu çalışma bunları çözmüş sayılmaz.
- Üretim sunucusu loopback üzerinde açıldı; sağlık yanıtı alındı.
  Kapalı API için 403 ve yazma isteği için 405 doğrulandı.
- Gerçek OSIRIS sayfasında depremler katmanını açma ve bütün katmanları
  kapatma durumları done olarak doğrulandı.
- Aynı gerçek sayfanın zoom testi WebGL2 GPUInitializationError nedeniyle
  unverified/state_timeout verdi. Bu test GEÇMEDİ. Katman durumu onayı,
  3D kürenin çizildiği veya kaynak verilerinin eksiksiz olduğu anlamına gelmez.
- Windows mikrofonu, cihaz geçişi ve gerçek küre üzerinde şehir/zoom kabulü bekliyor.
