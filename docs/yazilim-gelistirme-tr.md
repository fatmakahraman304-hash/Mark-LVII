# JARVIS yazılım geliştirme

Mevcut `dev_agent` yeni proje oluşturur, yerel projeleri geliştirir ve hata
kontrolleri yapar. `github_develop` kişisel Mark-LVII deposunu ayrı
`~/JarvisDevelopment/Mark-LVII` klasörüne alır.

Komut akışı: geliştirme alanını hazırla → incele → istenen değişikliği geliştir
→ test et → seçilen kaynak dosyalarını yayınla → kontroller bittiyse main'e al.
Yayınlama için Git ve GitHub CLI (`gh`) kurulu, kullanıcı hesabı bağlı olmalıdır.
Anahtarlar sohbete yazılmaz. Mevcut geliştirme işi bitmeden yayın yapılmaz.

Yayınlama seçilmiş dosyalardan commit ve PR oluşturur. GitHub kontrolleri
bekliyorsa veya başarısızsa birleştirme yapılmaz. Sonraki `merge` komutu doğru
commit, temiz çalışma alanı ve başarılı kontrolleri tekrar denetler.
Depo kuralları ve GitHub yetkileri ayrıca geçerlidir.

Main'e alınan sürüm mevcut GÜNCELLE düğmesiyle indirilir. Çalışan uygulamanın
klasöründe geliştirme yapılmaz. Diğer GitHub depolarını otomatik yayınlama bu
aracın kapsamında değildir; yerel kopyaları mevcut dev_agent ile incelenebilir.

Dosya kapsamı koruma testleri çalıştırıldı. Gerçek Windows GitHub oturumu,
modelle kod üretimi ve baştan sona yayınlama henüz cihazda denenmedi.
