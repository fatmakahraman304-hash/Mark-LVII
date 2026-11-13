# JARVIS + OSIRIS — geliştirme dalı

Bu sürüm kişisel 1080p arayüzünü, Murat Kahraman başlığını ve sol alttaki
şehir haritasını korur. OSIRIS geliştirmesi feature/osiris-world-command
dalındadır; gerçek Windows sesli kullanım kabulü tamamlanmadan nihai sürüm değildir.

## Mevcut özellikler

- Resmi siteyi veya izin verilen loopback adresini Qt penceresinde açma.
- Hazırlanmış yerel OSIRIS'te sayfayı yeniden yüklemeden katman açma,
  kapatma, temizleme; şehir arama, yakınlaştırma ve harita durumunu okuma.
- Komutlar Qt sinyaliyle ana iş parçacığına aktarılır; mikrofonu bekletmez.
- İlk yanıt yalnızca kuyruğa alındığını söyler. Gerçek harita durumuna göre
  etkinlik günlüğünde done, failed veya unverified sonucu görünür.
- done, görünümün doğrulandığını belirtir; veri kaynaklarının güncelliğini kanıtlamaz.
- QtWebEngine yoksa URL açma tarayıcıya düşer; anlık kontrol bu yolda yoktur.
- Çevrimiçi osirisai.live sayfasına köprü eklenmez; URL değişimi sayfayı yenileyebilir.

Örnekler: “OSIRIS'te sadece depremleri göster”, “Katmanları temizle”,
“OSIRIS'te Gazimağusa'ya git”, “OSIRIS'te yaklaş”, “OSIRIS harita durumunu oku”.
Ctrl+Shift+O, yapılandırılan yerel adresi de kullanır.

## Yerel servis hazırlığı

OSIRIS ayrı depoda kalır. Kaynak sürümü fa394afbc49f6eaa43446f7cc321590556cd665b.
Node.js 20.9+ gerekir. JARVIS bağımlılıkları kurulmuş Python ortamını kullanın.
JARVIS ve OSIRIS kardeş klasörler olduğunda:

    git clone https://github.com/simplifaisoul/osiris.git ../osiris
    git -C ../osiris checkout fa394afbc49f6eaa43446f7cc321590556cd665b
    npm --prefix ../osiris ci
    python tools/prepare_osiris.py ../osiris --build
    python tools/start_with_osiris.py ../osiris

Hazırlama betiği kaynak sürümünü ve değiştirilen dosyaların içeriklerini
kontrol eder; farklı kaynağı tahmin ederek değiştirmez. Kendi adapter dosyasını
ekler, React'in mevcut assistSite arayüzüne bağlar ve yerel salt-okuma HTTP
profilini kurar. Üretim derlemesi içerik parmak iziyle işaretlenir.
Eski/işaretsiz derleme başlatılmaz. Kaynak değişirse yeniden --build gerekir.

Başlatıcı yalnızca 127.0.0.1 üzerinde çalışır; port doluysa başka servisi
kapatmaz. Servis hazır olduktan sonra JARVIS'i açar. JARVIS kapanınca kendi
başlattığı süreçleri sonlandırır; OSIRIS çökerse çalışan JARVIS kapanmaz.
Log, Windows LOCALAPPDATA altında Jarvis/logs/osiris.log dosyasındadır.
Linux'ta ~/.local/share/Jarvis/logs/osiris.log kullanılır.
--check-only servis başlangıcını kontrol edip kapatır.
Başlatıcı yalnızca doğrulanmış üretim derlemesini kullanır.

## Sınırlar

Köprü yalnızca aynı yerel origin'in ana belgesinde çalışır. Her belge oturumunda
yeni belirteç, sınırlı komut şeması, 16 bekleyen komut sınırı ve zaman aşımı vardır.
Web sayfasına Python/shell/dosya erişimi verilmez. Dış origin yönlendirmeleri reddedilir.

Yerel HTTP profili yalnızca belirlenmiş GET/HEAD veri uçlarını açar. RECON,
SDK ingest, yazma işlemleri ve diğer API'ler kapalıdır. OSIRIS'in bütün bağımsız
özellikleri bu profilde kullanılabilir değildir. Bazı kaynaklar anahtar,
internet veya ek servis ister; boş veri başarı olarak sunulmaz.

## Testler

    python -m unittest discover -s tests -p test_osiris_world.py -v
    python -m unittest discover -s tests -p test_osiris_intel.py -v
    node --test tests/test_osiris_bridge.mjs
    python -m unittest discover -s tests -p test_osiris_qt.py -v
    python -m unittest discover -s tests -p test_location_map.py -v

Qt testi gerçek QtWebEngine içinde yerel test sayfası kullanır: komutlar boyunca
tek belge yüklemesi, katman/kamera durumu ve URL sınırını ölçer. Bu, gerçek
OSIRIS WebGL küresi veya Windows mikrofon testi değildir. GitHub Actions aynı
testleri Windows/Linux üzerinde çalıştırır.

## Kaynak ve lisanslar

- MARK LVII: https://github.com/FatihMakes/Mark-LVII — CC BY-NC 4.0
- OSIRIS: https://github.com/simplifaisoul/osiris — MIT

Upstream lisans dosyaları korunur. OSIRIS kaynak kodu JARVIS deposuna kopyalanmaz.
Deprem verisi resmi afet uyarısının yerini tutmaz.
