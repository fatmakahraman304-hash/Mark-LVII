package ai.jarvis.geminitv;

import android.app.Activity;
import android.Manifest;
import android.content.pm.PackageManager;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.graphics.Color;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.speech.RecognizerIntent;
import android.speech.RecognitionListener;
import android.speech.SpeechRecognizer;
import android.speech.tts.TextToSpeech;
import android.text.InputType;
import android.view.View;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.Spinner;
import android.widget.TextView;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * Gemini UI for Android 8+ / Android TV, with no vault password prompt.
 * Import a plain-text API key file once per Android device; it is then kept
 * encrypted at rest in Android Keystore and auto-unlocked on future launches.
 * No Ollama, laptop, Python or USB autorun.
 */
public final class MainActivity extends Activity {
    private static final int OPEN_KEY_FILE = 110;
    private static final int VOICE_INPUT = 120;
    private static final int MIC_PERMISSION = 130;
    private static final int BLUE = Color.rgb(120, 220, 255);
    private final ExecutorService worker = Executors.newSingleThreadExecutor();
    private final JSONArray history = new JSONArray();
    private TextView status, transcript, voiceInfo;
    private EditText prompt;
    private Button send, micButton, stopButton, soundButton;
    private Spinner model;
    private TextToSpeech tts;
    private SpeechRecognizer recognizer;
    private final Handler micHandler = new Handler(Looper.getMainLooper());
    private boolean listening = false;
    private final Runnable micTimeout = () -> { if (listening) stopListening(true); };
    private boolean voiceEnabled = true;
    private volatile boolean speakReady = false;
    private boolean busy = false;
    private String apiKey; // RAM-only; cleared when Activity dies

    private TextView text(String label, int size, int color) {
        TextView t = new TextView(this);
        t.setText(label);
        t.setTextSize(size);
        t.setTextColor(color);
        t.setPadding(0, 10, 0, 12);
        return t;
    }

    private Button button(String title) {
        Button b = new Button(this);
        b.setText(title);
        b.setTextSize(19);
        b.setMinHeight(72);
        b.setAllCaps(false);
        b.setFocusable(true);
        return b;
    }

    private EditText input(String hint, boolean password) {
        EditText e = new EditText(this);
        e.setHint(hint);
        e.setTextColor(Color.WHITE);
        e.setHintTextColor(Color.rgb(164, 189, 202));
        e.setTextSize(19);
        e.setSingleLine(password);
        e.setInputType(password ?
                InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD :
                InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_FLAG_MULTI_LINE);
        e.setMinHeight(72);
        return e;
    }

    @Override public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().setSoftInputMode(android.view.WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE);
        try { apiKey = DeviceKeyStore.load(this); }
        catch (Exception ignored) { apiKey = null; /* request re-import */ }
        ScrollView container = new ScrollView(this);
        container.setFillViewport(true);
        container.setBackgroundColor(Color.rgb(6, 19, 31));
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(28, 20, 28, 28);
        container.addView(root);
        setContentView(container);

        root.addView(text("J.A.R.V.I.S.", 36, BLUE));
        root.addView(text("GEMINI USB · Android TV / Projeksiyon", 17, Color.LTGRAY));
        status = text(apiKey == null ?
                "USB'den Gemini anahtar dosyanı içe aktar (şifre yok)." :
                "Gemini anahtarı bu Android cihazda kayıtlı, hazır.", 17, Color.rgb(175, 226, 201));
        root.addView(status);

        Button choose = button("USB'den Gemini anahtarını seç (şifresiz)");
        root.addView(choose);
        choose.setOnClickListener(v -> {
            Intent picker = new Intent(Intent.ACTION_OPEN_DOCUMENT);
            picker.addCategory(Intent.CATEGORY_OPENABLE);
            picker.setType("*/*");
            try { startActivityForResult(picker, OPEN_KEY_FILE); }
            catch (ActivityNotFoundException ex) {
                setStatus("Bu Android cihazda dosya seçici yok. Dosyayı cihazın İndirilenler klasörüne taşıyıp dosya yöneticisini kontrol et.");
            }
        });

        root.addView(text("Gemini modeli (FatihMakes'in metin Flash ailesi)", 16, Color.LTGRAY));
        model = new Spinner(this);
        ArrayAdapter<String> adapter = new ArrayAdapter<>(this,
                android.R.layout.simple_spinner_item, GeminiHttp.MODELS);
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        model.setAdapter(adapter);
        root.addView(model);

        transcript = text("JARVIS: Merhaba! İnternet bağlantın ve Gemini anahtarın varsa burada konuşabiliriz.\n",
                21, Color.WHITE);
        transcript.setMinHeight(180);
        transcript.setTextIsSelectable(true);
        root.addView(transcript);

        prompt = input("JARVIS'e mesajını yaz", false);
        root.addView(prompt);
        send = button("Gönder");
        send.setEnabled(apiKey != null);
        root.addView(send);
        send.setOnClickListener(v -> sendMessage());

        micButton = button("🎤 KONUŞ · Mikrofona seslen");
        root.addView(micButton);
        micButton.setOnClickListener(v -> startVoice());

        stopButton = button("⏹ Dinlemeyi Durdur");
        stopButton.setEnabled(false);
        root.addView(stopButton);
        stopButton.setOnClickListener(v -> stopListening(false));

        soundButton = button("🔇 Sesi Kapat");
        root.addView(soundButton);
        soundButton.setOnClickListener(v -> {
            voiceEnabled = !voiceEnabled;
            if (!voiceEnabled && tts != null) tts.stop();
            setStatus(voiceEnabled ? "Sesli yanıtlar açıldı." : "Sesli yanıtlar kapatıldı.");
            updateVoiceControls();
        });

        Button testSound = button("🔊 SES TESTİ · Merhaba de");
        root.addView(testSound);
        testSound.setOnClickListener(v -> testVoiceOutput());

        voiceInfo = text("Mikrofon ve Türkçe ses kontrol ediliyor…", 16, Color.LTGRAY);
        root.addView(voiceInfo);
        updateVoiceControls();

        Button clear = button("Sohbeti temizle");
        root.addView(clear);
        clear.setOnClickListener(v -> {
            while (history.length() > 0) history.remove(0);
            transcript.setText("JARVIS: Sohbet temizlendi.\n");
        });

        root.addView(text("USB anahtar dosyası ŞİFRESİZDİR: USB'yi bulan kişi Gemini anahtarını kullanabilir. "
                + "İçe aktarıldıktan sonra Android uygulaması anahtarı kendi Keystore şifrelemesiyle saklar. "
                + "Konuş'a bastığında mikrofon kısa süre dinlenir; sürekli dinleme veya gizli kayıt yok. "
                + "Konuşma tanıma hizmeti sesi sağlayıcısına internet üzerinden gönderebilir. "
                + "Yanıtı sesli okuma için Android TTS gerekir. Bunlar tüm TV'lerde yoktur. "
                + "Her Gemini isteği Google'a internet üzerinden gider; anahtar kotanı/bütçeni kontrol et.",
                14, Color.LTGRAY));
        tts = new TextToSpeech(this, code -> {
            micHandler.post(() -> {
                if (code == TextToSpeech.SUCCESS && tts != null) {
                    int result = tts.setLanguage(new Locale("tr", "TR"));
                    speakReady = result != TextToSpeech.LANG_MISSING_DATA
                            && result != TextToSpeech.LANG_NOT_SUPPORTED;
                    if (speakReady) {
                        tts.setSpeechRate(1.03f);
                        tts.setPitch(0.94f);
                    }
                }
                updateVoiceControls();
            });
        });
    }

    private void setStatus(String message) { status.setText(message); }

    private static String readBounded(InputStream input, int maxBytes) throws Exception {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        byte[] buffer = new byte[2048];
        int n;
        while ((n = input.read(buffer)) != -1) {
            if (out.size() + n > maxBytes) throw new Exception("File too big");
            out.write(buffer, 0, n);
        }
        return new String(out.toByteArray(), StandardCharsets.UTF_8);
    }

    @Override protected void onActivityResult(int request, int result, Intent data) {
        super.onActivityResult(request, result, data);
        if (request == OPEN_KEY_FILE && result == RESULT_OK && data != null && data.getData() != null) {
            try (InputStream stream = getContentResolver().openInputStream(data.getData())) {
                if (stream == null) throw new Exception("Missing file stream");
                String file = readBounded(stream, 4096);
                JSONObject obj = new JSONObject(file);
                String imported = obj.optString("api_key", "");
                if (obj.length() != 3 || obj.optInt("version") != 2
                        || !"gemini".equals(obj.optString("provider"))
                        || !imported.matches("[\\x21-\\x7e]{20,220}")) {
                    throw new Exception("Unsupported API key file");
                }
                DeviceKeyStore.save(this, imported);
                apiKey = imported;
                send.setEnabled(true);
                updateVoiceControls();
                setStatus("Gemini anahtarı kaydedildi. Konuş veya mesaj yaz.");
            } catch (Exception ex) {
                setStatus("Anahtar içe aktarılamadı. Yeni KEY-SETUP.html ile şifresiz jarvis-gemini-key.json oluştur.");
            }
        } else if (request == VOICE_INPUT && result == RESULT_OK && data != null) {
            ArrayList<String> words = data.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS);
            if (words != null && !words.isEmpty()) {
                prompt.setText(words.get(0));
                sendMessage();
            } else {
                setStatus("Mikrofon sesi algılamadı. Tekrar Konuş'a bas.");
            }
        } else if (request == VOICE_INPUT && result != RESULT_OK) {
            setStatus("Dinleme iptal edildi veya ses algılanmadı.");
        }
    }

    private void updateVoiceControls() {
        if (micButton != null) {
            micButton.setText(listening ? "🎤 DİNLİYOR…" : "🎤 KONUŞ · Mikrofona seslen");
            micButton.setEnabled(apiKey != null && !listening && !busy);
        }
        if (stopButton != null) stopButton.setEnabled(listening);
        if (soundButton != null) soundButton.setText(voiceEnabled ? "🔇 Sesi Kapat" : "🔊 Sesi Aç");
        if (voiceInfo != null) {
            String inputStatus;
            try {
                inputStatus = SpeechRecognizer.isRecognitionAvailable(this)
                        ? "Mikrofon tanıma servisi: var"
                        : "Mikrofon tanıma servisi: yok (harici uygulama denenebilir)";
            } catch (RuntimeException e) {
                inputStatus = "Mikrofon tanıma servisi: kontrol edilemedi";
            }
            voiceInfo.setText(inputStatus + " · Türkçe seslendirme: "
                    + (speakReady ? "hazır" : "henüz hazır değil"));
        }
    }

    private void testVoiceOutput() {
        if (!speakReady || tts == null) {
            setStatus("Türkçe ses motoru bulunamadı. Android seslendirme ayarlarında Türkçe TTS yükle.");
            return;
        }
        try {
            int result = tts.speak("Merhaba. Ben JARVIS. Sesim duyuluyor mu?",
                    TextToSpeech.QUEUE_FLUSH, null, "jarvis-test");
            setStatus(result == TextToSpeech.ERROR
                    ? "Ses motoru test cümlesini okuyamadı."
                    : "Ses testi oynatılıyor. Ses seviyesini kontrol et.");
        } catch (RuntimeException e) {
            setStatus("Android ses motoru yanıt vermedi.");
        }
    }

    private void stopListening(boolean timedOut) {
        if (!listening) return;
        listening = false;
        micHandler.removeCallbacks(micTimeout);
        if (recognizer != null) {
            try { recognizer.cancel(); } catch (RuntimeException ignored) { }
            try { recognizer.destroy(); } catch (RuntimeException ignored) { }
            recognizer = null;
        }
        updateVoiceControls();
        setStatus(timedOut ? "Mikrofon zaman aşımına uğradı. Tekrar Konuş'a bas."
                : "Dinleme durduruldu. Mikrofon kapalı.");
    }

    private void startVoice() {
        if (apiKey == null) {
            setStatus("Önce Gemini anahtarını USB dosyasından içe aktar.");
            return;
        }
        if (busy || listening) {
            setStatus("Mevcut yanıtın veya dinlemenin bitmesini bekle.");
            return;
        }
        if (tts != null) tts.stop(); // No speaker echo in microphone.
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO)
                != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO}, MIC_PERMISSION);
            return;
        }
        startMicrophone();
    }

    @Override public void onRequestPermissionsResult(int requestCode,
            String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == MIC_PERMISSION) {
            if (grantResults.length > 0 &&
                    grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                startMicrophone();
            } else {
                setStatus("Mikrofon izni verilmedi. Android Uygulama Ayarları'ndan mikrofon iznini aç.");
            }
        }
    }

    private void startMicrophone() {
        if (apiKey == null || busy || listening) return;
        try {
            if (!SpeechRecognizer.isRecognitionAvailable(this)) {
                startExternalRecognition();
                return;
            }
            recognizer = SpeechRecognizer.createSpeechRecognizer(this);
            recognizer.setRecognitionListener(new RecognitionListener() {
                @Override public void onReadyForSpeech(Bundle params) {
                    if (listening) setStatus("🎤 JARVIS dinliyor… Şimdi konuş.");
                }
                @Override public void onBeginningOfSpeech() {
                    if (listening) setStatus("🎤 Sesin algılandı. Konuşmaya devam et.");
                }
                @Override public void onRmsChanged(float rmsdB) { }
                @Override public void onBufferReceived(byte[] buffer) { }
                @Override public void onEndOfSpeech() {
                    if (listening) setStatus("Sözlerin işleniyor…");
                }
                @Override public void onError(int error) {
                    if (!listening) return;
                    stopListening(false);
                    switch (error) {
                        case SpeechRecognizer.ERROR_NO_MATCH:
                        case SpeechRecognizer.ERROR_SPEECH_TIMEOUT:
                            setStatus("Seni anlayamadım. Konuş'a tekrar bas.");
                            break;
                        case SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS:
                            setStatus("Mikrofon izni yok. Android ayarlarını kontrol et.");
                            break;
                        case SpeechRecognizer.ERROR_NETWORK:
                        case SpeechRecognizer.ERROR_NETWORK_TIMEOUT:
                            setStatus("Konuşma tanıma hizmeti internete bağlanamadı.");
                            break;
                        case SpeechRecognizer.ERROR_RECOGNIZER_BUSY:
                            setStatus("Mikrofon başka bir hizmet tarafından kullanılıyor.");
                            break;
                        default:
                            setStatus("Konuşma tanıma hatası (" + error
                                    + "). Cihazın konuşma tanıma servisini kontrol et.");
                    }
                }
                @Override public void onResults(Bundle results) {
                    if (!listening) return;
                    ArrayList<String> words =
                            results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
                    stopListening(false);
                    if (words == null || words.isEmpty() || words.get(0).trim().isEmpty()) {
                        setStatus("Sözler duyulamadı. Tekrar Konuş'a bas.");
                        return;
                    }
                    prompt.setText(words.get(0));
                    sendMessage(); // One explicit mic activation sends just one recognized turn.
                }
                @Override public void onPartialResults(Bundle partialResults) {
                    if (!listening) return;
                    ArrayList<String> words =
                            partialResults.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
                    if (words != null && !words.isEmpty()) {
                        String heard = words.get(0);
                        setStatus("🎤 Duyduğum: " + heard.substring(0, Math.min(heard.length(), 110)));
                    }
                }
                @Override public void onEvent(int eventType, Bundle params) { }
            });
            Intent intent = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
            intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                    RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
            intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, "tr-TR");
            intent.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true);
            intent.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1);
            listening = true;
            updateVoiceControls();
            setStatus("🎤 Mikrofon açılıyor…");
            recognizer.startListening(intent);
            micHandler.postDelayed(micTimeout, 20000L);
        } catch (RuntimeException ex) {
            if (listening) stopListening(false);
            if (recognizer != null) {
                try { recognizer.destroy(); } catch (RuntimeException ignored) { }
                recognizer = null;
            }
            startExternalRecognition();
        }
    }

    private void startExternalRecognition() {
        Intent intent = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, "tr-TR");
        intent.putExtra(RecognizerIntent.EXTRA_PROMPT, "JARVIS dinliyor…");
        try {
            setStatus("Android ses tanıma ekranı açılıyor…");
            startActivityForResult(intent, VOICE_INPUT);
        } catch (ActivityNotFoundException | SecurityException ex) {
            setStatus("Bu Android cihazda mikrofon / ses tanıma hizmeti yok. "
                    + "USB mikrofon ve Android konuşma tanıma hizmeti gerekebilir.");
        }
    }

    private void appendConversation(String speaker, String line) {
        String next = transcript.getText().toString() + "\n" + speaker + ": " + line + "\n";
        if (next.length() > 14000) next = next.substring(next.length() - 14000);
        transcript.setText(next);
    }

    private void sendMessage() {
        if (busy || apiKey == null) { setStatus("Gemini anahtarını içe aktar veya mevcut yanıtı bekle."); return; }
        String question = prompt.getText().toString().trim();
        if (question.isEmpty() || question.length() > 2000) {
            setStatus("Mesaj 1-2000 karakter olmalı.");
            return;
        }
        String selected = String.valueOf(model.getSelectedItem());
        String keyForRequest = apiKey;
        if (!GeminiHttp.allowedModel(selected)) { setStatus("Model desteklenmiyor."); return; }
        busy = true;
        send.setEnabled(false);
        updateVoiceControls();
        prompt.setText("");
        appendConversation("SEN", question);
        setStatus("Gemini cevap hazırlıyor…");
        worker.execute(() -> {
            try {
                String result = GeminiHttp.ask(keyForRequest, selected, history, question);
                runOnUiThread(() -> {
                    try {
                        history.put(new JSONObject().put("role", "user").put("text", question));
                        history.put(new JSONObject().put("role", "model").put("text", result));
                        while (history.length() > 8) history.remove(0);
                    } catch (Exception ignored) { /* UI still displays answer */ }
                    appendConversation("JARVIS", result);
                    setStatus("Hazır · " + selected);
                    busy = false;
                    send.setEnabled(true);
                    updateVoiceControls();
                    if (voiceEnabled && speakReady && tts != null) {
                        try {
                            int spoken = tts.speak(
                                    result.substring(0, Math.min(result.length(), 3000)),
                                    TextToSpeech.QUEUE_FLUSH, null, "jarvis-answer");
                            if (spoken == TextToSpeech.ERROR)
                                setStatus("Yanıt yazıldı; Android ses motoru konuşamadı.");
                        } catch (RuntimeException ignored) {
                            setStatus("Yanıt yazıldı; ses motoru kullanılamıyor.");
                        }
                    } else if (voiceEnabled && !speakReady) {
                        setStatus("Yanıt yazıldı; Türkçe ses motoru hazır değil. SES TESTİ'ni dene.");
                    }
                });
            } catch (Exception ex) {
                // Never log API credentials, network bodies, or prompts.
                final String message = ex instanceof java.io.IOException ?
                        ex.getMessage() : "Gemini yanıtı işlenemedi.";
                runOnUiThread(() -> {
                    appendConversation("JARVIS", "İstek başarısız: " + message);
                    setStatus("Bağlantıyı, Gemini anahtarını ve kotayı kontrol et.");
                    busy = false; send.setEnabled(true); updateVoiceControls();
                });
            }
        });
    }

    @Override protected void onStop() {
        stopListening(false); // Microphone must never stay on in the background.
        super.onStop();
    }

    @Override protected void onDestroy() {
        stopListening(false);
        micHandler.removeCallbacks(micTimeout);
        apiKey = null;
        speakReady = false;
        if (tts != null) { tts.stop(); tts.shutdown(); }
        worker.shutdownNow();
        super.onDestroy();
    }
}
