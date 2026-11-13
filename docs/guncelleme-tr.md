# JARVIS Güncelle düğmesi

Üst çubuktaki **GÜNCELLE** düğmesi GitHub’daki mevcut dalı kontrol eder,
yeni kodu indirir ve uygular. İşlem arka planda çalışır. Sonuç hem bildirimde
hem etkinlik günlüğünde görünür. Başarılı güncellemeden sonra uygulamayı kapatıp
yeniden açın; çalışan ses oturumu zorla kesilmez.

- Git kurulumu mevcut dalı takip eder; yalnızca ileri yönlü birleştirme yapar.
  Yerel kod değişikliklerinde durur. Eski sürüm `jarvis-backup/` dalında tutulur.
- ZIP kurulumu `update_channel.json` içindeki dalı takip eder. Bu geliştirme
  sürümünün kanalı `feature/osiris-world-command` dalıdır; ana sürüme geçiş yapmaz.
- ZIP kurulumu değişen dosyaları `.jarvis-backups/` içine yedekler. Yazma hatasında
  değişiklikleri geri alır. Sonraki güncellemelerde yerel kod değişikliklerini korur.
- Anahtarlar, ayarlar, hafıza verileri, günlükler ve özel dosyalar korunur.
- Yeni bağımlılık gerektiren sürümlerde, Windows’un açık Qt/ses DLL’lerini
  değiştirmek yerine işlem durur ve yeni sürümün `setup.py` kurulumu istenir.
  EXE paketleri için de yeni kurulum paketi gerekir.
- İnternet hatası başarı olarak gösterilmez. Kontrol/indirme sırasında kod değişmez.
- İlk kez düğmeyi alabilmek için bu kodu içeren sürümün kurulması gerekir;
  düğme eski kurulumda kendiliğinden belirmez.

Otomatik testler ZIP kontrol/uygulama, güncel sürüm, ayar koruması, güvenli arşiv,
yerel değişiklik, silinen kaynak dosyası, rollback, ağ hatası, eşzamanlı işlem
kilidi ve bağımlılık değişimini kapsar. Gerçek Windows cihazında güncelleme ve
uygulamanın tekrar açılması ayrıca denenmelidir.
