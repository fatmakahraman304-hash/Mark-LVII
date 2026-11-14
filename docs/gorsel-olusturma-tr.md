# JARVIS resim oluşturma — Nano Banana 2 Lite ve ücretsiz yerel seçenek

## Kullanıcının gördüğü hata

JARVIS'in eski `generate_image` eklentisi doğrudan
`gemini-3.1-flash-lite-image` (Nano Banana 2 Lite) modelini çağırıyordu.
Model adı geçerli, ancak **Gemini API ücretsiz katmanında görsel üretimi
sunulmuyor**. Sesli sohbetin çalışması, görüntü üretebildiği anlamına gelmez.

Resmî kaynaklar:
- https://ai.google.dev/gemini-api/docs/models
- https://ai.google.dev/gemini-api/docs/pricing
- https://ai.google.dev/gemini-api/docs/image-generation

Bunun bir **Gemini API**, Google AI Studio veya başka hizmet ödemesi
olduğuna dikkat edin. ChatGPT Plus aboneliği bunu karşılamaz.

## Yeni çalışma biçimi

JARVIS kullanıcı "resim oluştur" dediğinde:

1. `http://127.0.0.1:8188` adresindeki **yerel ComfyUI** servisini kontrol eder.
2. ComfyUI açıksa ve uyumlu bir SDXL/SD1.5 checkpoint yüklüyse işi **yalnızca
   yerel** sunucuda yapar; sonucu JARVIS'in ortadaki resim alanında gösterir.
3. Sonuç bilgisayarda `downloads/images/` içine kaydedilir.
4. ComfyUI yoksa, model bulunamadıysa veya hata olursa JARVIS sebebini açıkça
   söyler. **Ücretli API'ye kendiliğinden geçmez.**

Örnek sesli komut:
- "Jarvis, deniz kenarında fütüristik bir ev resmi oluştur."
- "Jarvis, resimdeki evin dış cephesini beyaz yap." (Resmi COMMAND dosya
  alanına bıraktıktan sonra veya JARVIS'in daha önce oluşturduğu görüntü için.)

### ComfyUI kurulumu (ücretsiz yerel yöntem)

1. https://comfy.org/download üzerinden resmî ComfyUI masaüstü uygulamasını
   Windows'a kurun.
2. ComfyUI içinde **SDXL veya SD1.5 uyumlu tek-dosya checkpoint**
   (`.safetensors`) modeli yükleyin. Tercihen programın model yöneticisinden.
   Model lisansını ve boyutunu kontrol edin. İndirmenin büyük olabileceğini
   ve makinenin GPU/RAM özelliklerine bağlı çalışacağını unutmayın.
3. ComfyUI'yi çalıştırın. Yerel HTTP sunucusunun
   `http://127.0.0.1:8188/` adresinde hazır olduğundan emin olun.
4. JARVIS'i açın ve "resim oluştur" deyin. Sonuç JARVIS içinden görünür.

Eklenti ComfyUI'yi kendisi **kurmaz, açmaz veya model indirmez**.
Bu aşama SD1.5 ve SDXL'in standart ComfyUI checkpoint iş akışını kullanır;
Flux, SD3, özel node'lar ve başka mimariler henüz desteklenmez.
Sistemde uyumlu GPU yoksa oluşturma yavaş olabilir veya başarısız olabilir.
İnternete bağlantı olmadan üretim, ComfyUI ve model daha önce indirildiyse
mümkündür.

### İsteğe bağlı farklı yerel ComfyUI portu

Varsayılan `127.0.0.1:8188`. Port farklıysa JARVIS'i başlatan
PowerShell oturumunda `JARVIS_COMFY_URL` ortam değişkeni atanabilir.
Güvenlik gereği yalnızca loopback HTTP adresleri kabul edilir; ağ IP'leri,
uzak sunucular ve internet adresleri reddedilir.

### Gemini Nano Banana 2 Lite ücretli API (varsayılan olarak kapalı)

Ücretli Gemini görsel API yolu **özellikle devre dışıdır**. Kullanıcı
faturalandırmayı kendisi etkinleştirmeden hiçbir ücretli görsel API
çağrısı yapılmaz.

İleride bilinçli olarak ücretli Gemini seçilirse, kullanıcının
Google AI Studio projesinde faturalandırmayı ve maliyet sınırlarını
kontrol etmesi, ayrıca JARVIS için `JARVIS_ALLOW_PAID_IMAGES=1`
ortam değişkenini açıkça ayarlaması gerekir. Bu opt-in:
- JARVIS'in Google hesabında faturalandırmayı kendisi açmaz,
- fiyatları veya kotayı garanti etmez,
- sadece kullanıcı zaten aktif faturalandırmayı doğruladıysa
  ücretli görsel çağrısı yapılmasına izin verir.

**Güvenlik:** API anahtarı veya ödeme bilgileri sohbete / GitHub'a
yüklenmemeli. Gerekli anahtar yalnızca JARVIS'in yerel gizli
yapılandırmasından okunur.

## Teknik sınırlar ve test

- `core/local_image.py` yalnızca loopback'e bağlanır; HTTP yönlendirmeleri,
  proxy, keyfi sunucular reddedilir.
- ComfyUI API: `/models/checkpoints`, `/prompt`, `/history/{id}`,
  `/view`, düzenlemede `/upload/image`.
- Büyük yanıtlar reddedilir. Gönderilen düzenleme görseli yalnızca kullanıcının
  dosya alanına bıraktığı görsel veya JARVIS'in son ürettiği görüntüdür.
- Testler ağ isteklerini taklit eder; gerçek ComfyUI + Windows/GPU testleri
  ayrıca gereklidir. Test geçti diye modelin gerçekten resim üretildiği
  iddia edilmez.
