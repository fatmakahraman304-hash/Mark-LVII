# MARK LVII + OSIRIS — Dünya Komuta Merkezi (Aşama 1)

Bu klasördeki `plugins/osiris_world.py`, JARVIS'in **sesli komutlarıyla**
OSIRIS'in resmi dünya haritasını tarayıcıda açar ve **URL tabanlı** harita
katmanlarını değiştirir. Orijinal MARK LVII arayüzünü, Gemini oturumunu veya
ses altyapısını değiştirmez. Python bağımlılığı eklemez.

> Durum: İlk entegrasyon / tarayıcı köprüsü. Gömülü Qt haritası, mevcut
> sekmeyi gerçek zamanlı değiştirme, canlı veri okumak ve OSIRIS'i Windows'ta
> otomatik başlatmak **henüz yok**. Sesli komuttan sonra yeni sekme açılabilir.

## Kullanım

JARVIS yeniden başlatıldığında `plugins/osiris_world.py` otomatik yüklenir.
Örnekler:

- "Jarvis, OSIRIS dünya haritasını aç."
- "Jarvis, OSIRIS'te sadece depremleri göster."
- "Jarvis, uçak ve gemi katmanlarını ekle."
- "Jarvis, kamera katmanını gizle."
- "Jarvis, uzay görünümünü aç."
- "Jarvis, OSIRIS harita katmanlarını temizle."
- "Jarvis, varsayılan dünya görünümüne dön."

Eklentinin API'si:

| Mode | Etki |
| --- | --- |
| `open` / `reset` | OSIRIS'in varsayılan veri katmanlarını seçer |
| `show` | Adı verilen katmanları seçime ekler |
| `hide` | Seçimden kaldırır |
| `focus` | Yalnızca verilen katmanları seçer |
| `preset` | `world`, `air`, `sea`, `space`, `cameras`, `disasters`, `weather`, `news` |
| `clear` | Harita veri katmanlarını sıfırlar |

OSIRIS, harita açılırken `?layers=earthquakes,cctv` biçimini okuyup
katmanlarını ayarlar. Komutlar aynı tarayıcı sekmesinin durumunu değiştirmez;
tarayıcı URL'si değiştiğinde farklı bir sekmede açılabilir. JARVIS'in kendi
seçim hafızası yalnızca çalışan uygulama oturumu boyunca tutulur.

## Yerel OSIRIS (isteğe bağlı, daha sonra)

Bu ilk aşama varsayılan olarak `https://osirisai.live/` kullanır.
OSIRIS'i ayrıca yerel kurduktan sonra Windows'ta JARVIS'i başlatmadan önce:

```powershell
$env:JARVIS_OSIRIS_URL = "http://127.0.0.1:3000/"
cd C:\Fatih-JARVIS
.\.venv\Scripts\python.exe main.py
```

Eklenti **kendiliğinden** OSIRIS sunucusu kurmaz veya başlatmaz. Yalnızca
resmi HTTPS sitesi ve `localhost/127.0.0.1/::1` loopback adreslerine izin verir;
harici/IP adresi veya kullanıcının keyfi URL'si kabul edilmez.

## Kaynaklar ve kısıtlar

- MARK LVII: https://github.com/FatihMakes/Mark-LVII — CC BY-NC 4.0
- OSIRIS: https://github.com/simplifaisoul/osiris — MIT
- OSIRIS web sitesi: https://osirisai.live/

OSIRIS'in kaynak kodu projeye kopyalanmaz; yalnızca yayımlanmış katman
bağlantısı biçimi kullanılır. Veri kaynaklarının çalışması, gecikmesi ve
lisans koşulları OSIRIS'in sunucusuna ve üçüncü taraf sağlayıcılara bağlıdır.
Kamera bağlantıları yalnızca halka açık yayınlar içindir. Uydu ve uçuş
konumları gerçek zamanlı veya eksiksiz olmak zorunda değildir.

Eklenti harita içeriğini **okumaz**. JARVIS veri doğrulaması yapmadan uçak,
olay veya deprem görüldüğünü iddia etmemelidir. Tarayıcının açma isteğini
kabul etmesi, sitenin tamamen yüklendiğini kanıtlamaz.

## Test

Proje kökünde:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_osiris_world.py -v
```

Testler tarayıcıyı mock'lar; GUI/ses/Gemini/Windows testi yerine geçmez.

## Sonraki geliştirme aşamaları

1. Windows'ta eklentinin sesli model tarafından çağrıldığını doğrula.
2. Gömülü harita penceresi ve tek sekmede anlık katman kontrolü için
   güvenli, izinli köprü tasarla.
3. OSIRIS yerel servis başlatma/sağlık denetimi ve API veri okuma katmanını
   ayrı PR'larla ekle.
4. Yetkilendirme, önbellek, hız limiti, kaynak atfı ve Windows GUI testleri.
