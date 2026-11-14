package ai.jarvis.geminitv;

import android.Manifest;
import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.speech.RecognitionListener;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;
import android.speech.tts.TextToSpeech;
import android.speech.tts.UtteranceProgressListener;
import android.text.InputType;
import android.view.KeyEvent;
import android.view.inputmethod.EditorInfo;
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
 * Foreground-only, button-free voice interaction prototype.
 * Android SpeechRecognizer is NOT designed as a reliable continuous hotword
 * engine. Best-effort short recognition sessions are restarted in foreground.
 * "Sus" mutes spoken replies but microphone continues listening for "Konuş".
 * No background recording; never claims USB autorun or Gemini Live streaming.
 */
public final class MainActivity extends Activity {
    private static final int OPEN_KEY_FILE = 110;
    private static final int MIC_PERMISSION = 130;
    private static final long SESSION_TIMEOUT_MS = 20000L;
    private static final int MAX_SERVICE_FAILURES = 5;
    private static final int SKY = Color.rgb(123, 223, 255);
    private final Handler ui = new Handler(Looper.getMainLooper());
    private final ExecutorService worker = Executors.newSingleThreadExecutor();
    private final JSONArray history = new JSONArray();
    private boolean listening = false;
    private final Runnable microphoneTimeout = () -> {
        if (listening) {
            releaseRecognizer();
            scheduleListen(900);
        }
    };
    private final Runnable nextListen = this::startRecognition;

    private TextView status, conversation, micIndicator;
    private EditText prompt;
    private Button keyPicker;
    private Spinner model;
    private SpeechRecognizer recognizer;
    private TextToSpeech tts;
    private String apiKey;
    private String mostRecentAnswer = "";
    private boolean foreground = false;
    private boolean destroyed = false;
    private boolean speaking = false;
    private boolean busy = false;
    private boolean voiceEnabled = true;
    private boolean ttsReady = false;
    private boolean greetingPlayed = false;
    private int serviceFailures = 0;

    private TextView makeText(String title, int sp, int color) {
        TextView value = new TextView(this);
        value.setText(title);
        value.setTextSize(sp);
        value.setTextColor(color);
        value.setPadding(0, 12, 0, 12);
        return value;
    }

    private void setStatus(String value) {
        if (status != null) status.setText(value);
    }

    private void setMic(String value) {
        if (micIndicator != null) micIndicator.setText(value);
    }

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().setSoftInputMode(android.view.WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE);
        try { apiKey = DeviceKeyStore.load(this); }
        catch (Exception ignored) { apiKey = null; }

        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        scroll.setBackgroundColor(Color.rgb(6, 17, 29));
        LinearLayout root = new LinearLayout(this);
        root.setPadding(30, 20, 30, 28);
        root.setOrientation(LinearLayout.VERTICAL);
        scroll.addView(root);
        setContentView(scroll);

        root.addView(makeText("J.A.R.V.I.S.", 40, SKY));
        root.addView(makeText("NEXUS · GEMINI · ELLER SERBEST SES MODU", 17, Color.LTGRAY));
        status = makeText("Başlatılıyor…", 20, SKY);
        root.addView(status);
        micIndicator = makeText("● MİKROFON KAPALI", 20, Color.rgb(245, 187, 131));
        root.addView(micIndicator);
        root.addView(makeText("Bana normal konuş. \"Sus\" dersen sesimi kapatırım; "
                + "\"Konuş\" dersen yeniden sesli yanıt veririm.", 20, Color.WHITE));

        keyPicker = new Button(this);
        keyPicker.setText("Gemini anahtar dosyasını seç · İlk kurulum");
        keyPicker.setTextSize(19);
        keyPicker.setMinHeight(68);
        keyPicker.setAllCaps(false);
        root.addView(keyPicker);
        keyPicker.setVisibility(apiKey == null ? Button.VISIBLE : Button.GONE);
        keyPicker.setOnClickListener(v -> chooseKeyFile());

        model = new Spinner(this);
        ArrayAdapter<String> adapter = new ArrayAdapter<>(this,
                android.R.layout.simple_spinner_item, GeminiHttp.MODELS);
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        model.setAdapter(adapter);
        root.addView(makeText("Gemini modeli", 15, Color.LTGRAY));
        root.addView(model);

        conversation = makeText("JARVIS: Merhaba. Sesli konuşmaya hazırım.\n", 21, Color.WHITE);
        conversation.setMinHeight(270);
        conversation.setTextIsSelectable(true);
        root.addView(conversation);

        // Fallback only for TV devices lacking microphone/STT. No send button.
        prompt = new EditText(this);
        prompt.setTextColor(Color.WHITE);
        prompt.setHintTextColor(Color.LTGRAY);
        prompt.setHint("Mikrofon yoksa buraya yaz ve Enter'a bas");
        prompt.setTextSize(19);
        prompt.setSingleLine(true);
        prompt.setImeOptions(EditorInfo.IME_ACTION_SEND);
        prompt.setInputType(InputType.TYPE_CLASS_TEXT);
        prompt.setOnEditorActionListener((field, action, event) -> {
            if (action == EditorInfo.IME_ACTION_SEND ||
                    (event != null && event.getKeyCode() == KeyEvent.KEYCODE_ENTER
                            && event.getAction() == KeyEvent.ACTION_DOWN)) {
                sendMessage(prompt.getText().toString());
                return true;
            }
            return false;
        });
        root.addView(prompt);
        root.addView(makeText("Mikrofon yalnızca uygulama ekrandayken dinler. "
                + "Android konuşma tanıma servisi sesini kendi sunucusuna gönderebilir. "
                + "Soruların metni Gemini API'ye gönderilir. Uygulamayı kapatırsan dinleme durur. "
                + "USB'de şifresiz API anahtarı varsa USB'yi başkalarıyla paylaşma.",
                14, Color.LTGRAY));
        if (apiKey == null) {
            setStatus("İlk kurulum: USB'den jarvis-gemini-key.json seç.");
        } else {
            setStatus("Gemini anahtarı hazır · Türkçe ses başlatılıyor…");
        }
        configureTts();
    }

    private void chooseKeyFile() {
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        intent.addCategory(Intent.CATEGORY_OPENABLE);
        intent.setType("*/*");
        try { startActivityForResult(intent, OPEN_KEY_FILE); }
        catch (ActivityNotFoundException ex) {
            setStatus("Android dosya seçicisi yok. USB dosyasını cihazdaki dosya yöneticisiyle açmayı dene.");
        }
    }

    private void configureTts() {
        tts = new TextToSpeech(this, result -> ui.post(() -> {
            if (destroyed) return;
            if (result == TextToSpeech.SUCCESS && tts != null) {
                int language = tts.setLanguage(new Locale("tr", "TR"));
                ttsReady = language != TextToSpeech.LANG_MISSING_DATA
                        && language != TextToSpeech.LANG_NOT_SUPPORTED;
                if (ttsReady) {
                    tts.setSpeechRate(1.04f);
                    tts.setPitch(0.96f);
                    tts.setOnUtteranceProgressListener(new UtteranceProgressListener() {
                        @Override public void onStart(String id) { }
                        @Override public void onDone(String id) {
                            ui.post(() -> {
                                if (destroyed) return;
                                speaking = false;
                                scheduleListen(300);
                            });
                        }
                        @Override public void onError(String id) {
                            ui.post(() -> {
                                if (destroyed) return;
                                speaking = false;
                                setStatus("Android Türkçe ses motoru ses çıkaramadı.");
                                scheduleListen(350);
                            });
                        }
                        @Override public void onStop(String id, boolean interrupted) {
                            ui.post(() -> {
                                if (destroyed) return;
                                speaking = false;
                                scheduleListen(350);
                            });
                        }
                    });
                }
            }
            if (!ttsReady) setStatus("Türkçe TTS bulunamadı. Yazılı yanıt ve varsa mikrofon kullanılabilir.");
            maybeGreet();
        }));
    }

    private void maybeGreet() {
        if (!foreground || apiKey == null || greetingPlayed) return;
        if (ttsReady) {
            greetingPlayed = true;
            say("Merhaba. Ben JARVIS. Seni dinliyorum.", "jarvis-welcome");
        } else {
            setStatus("JARVIS hazır. Cihazda Türkçe TTS yoksa sesli cevap verilemez.");
        }
    }

    private void say(String message, String utteranceId) {
        if (!foreground || !voiceEnabled || !ttsReady || tts == null) return;
        try {
            speaking = true;
            int queued = tts.speak(message, TextToSpeech.QUEUE_FLUSH, null, utteranceId);
            if (queued == TextToSpeech.ERROR) {
                speaking = false;
                setStatus("Türkçe seslendirme başarısız. Android TTS kurulumunu kontrol et.");
            }
        } catch (RuntimeException ex) {
            speaking = false;
            setStatus("Android ses motoru çalışmadı.");
        }
    }

    private void releaseRecognizer() {
        listening = false;
        ui.removeCallbacks(microphoneTimeout);
        if (recognizer != null) {
            try { recognizer.cancel(); } catch (RuntimeException ignored) { }
            try { recognizer.destroy(); } catch (RuntimeException ignored) { }
            recognizer = null;
        }
        setMic("● MİKROFON KAPALI");
    }

    private void scheduleListen(long waitMs) {
        ui.removeCallbacks(nextListen);
        if (!foreground || destroyed || apiKey == null
                || serviceFailures >= MAX_SERVICE_FAILURES) return;
        ui.postDelayed(nextListen, waitMs);
    }

    private void ensureMicPermission() {
        if (!foreground || destroyed || apiKey == null) return;
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO)
                != PackageManager.PERMISSION_GRANTED) {
            setStatus("JARVIS'in seni duyabilmesi için Android mikrofon izni gerekiyor.");
            requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO}, MIC_PERMISSION);
            return;
        }
        scheduleListen(400);
    }

    @Override public void onRequestPermissionsResult(int request,
            String[] permissions, int[] grants) {
        super.onRequestPermissionsResult(request, permissions, grants);
        if (request != MIC_PERMISSION) return;
        if (grants.length > 0 && grants[0] == PackageManager.PERMISSION_GRANTED) {
            setStatus("Mikrofon izni verildi. JARVIS dinlemeye başlıyor.");
            scheduleListen(300);
        } else {
            setMic("● MİKROFON İZNİ VERİLMEDİ");
            setStatus("Mikrofon izni reddedildi. Android Uygulama Ayarları'ndan izin ver; yazılı sohbet kullanılabilir.");
        }
    }

    private void startRecognition() {
        if (!foreground || destroyed || apiKey == null || listening
                || serviceFailures >= MAX_SERVICE_FAILURES) return;
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO)
                != PackageManager.PERMISSION_GRANTED) return;
        try {
            if (!SpeechRecognizer.isRecognitionAvailable(this)) {
                serviceFailures = MAX_SERVICE_FAILURES;
                setMic("● MİKROFON HİZMETİ YOK");
                setStatus("Bu cihazda Android konuşma tanıma hizmeti bulunamadı. "
                        + "Uyumlu mikrofon ve konuşma tanıma servisi gerekir.");
                return;
            }
            recognizer = SpeechRecognizer.createSpeechRecognizer(this);
            recognizer.setRecognitionListener(new RecognitionListener() {
                @Override public void onReadyForSpeech(Bundle params) {
                    if (listening) setMic("● DİNLİYOR · KONUSABİLİRSİN");
                }
                @Override public void onBeginningOfSpeech() {
                    if (listening) setMic("● SES ALGILANDI");
                }
                @Override public void onRmsChanged(float rms) { }
                @Override public void onBufferReceived(byte[] b) { }
                @Override public void onEndOfSpeech() {
                    if (listening) setMic("● KONUŞMA İŞLENİYOR");
                }
                @Override public void onError(int code) { speechError(code); }
                @Override public void onResults(Bundle results) {
                    if (!listening) return;
                    ArrayList<String> words = results.getStringArrayList(
                            SpeechRecognizer.RESULTS_RECOGNITION);
                    releaseRecognizer();
                    serviceFailures = 0;
                    if (words != null && !words.isEmpty()) {
                        handleUtterance(words.get(0));
                    }
                    scheduleListen(500);
                }
                @Override public void onPartialResults(Bundle result) {
                    if (!listening) return;
                    ArrayList<String> words = result.getStringArrayList(
                            SpeechRecognizer.RESULTS_RECOGNITION);
                    if (words != null && !words.isEmpty()) {
                        String heard = words.get(0);
                        setMic("● DUYULAN: " + heard.substring(0, Math.min(heard.length(), 75)));
                        // Only full results are considered valid commands to avoid echo/false positives.
                    }
                }
                @Override public void onEvent(int eventType, Bundle data) { }
            });
            Intent request = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
            request.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                    RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
            request.putExtra(RecognizerIntent.EXTRA_LANGUAGE, "tr-TR");
            request.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true);
            request.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1);
            listening = true;
            setMic("● MİKROFON AÇILIYOR");
            recognizer.startListening(request);
            ui.postDelayed(microphoneTimeout, SESSION_TIMEOUT_MS);
        } catch (RuntimeException ex) {
            releaseRecognizer();
            serviceFailures++;
            if (serviceFailures >= MAX_SERVICE_FAILURES) {
                setStatus("Android mikrofon hizmeti başlatılamadı. Cihazı/uygulamayı yeniden aç.");
            } else {
                scheduleListen(1800L * serviceFailures);
            }
        }
    }

    private void speechError(int code) {
        if (!listening) return;
        releaseRecognizer();
        if (code == SpeechRecognizer.ERROR_NO_MATCH
                || code == SpeechRecognizer.ERROR_SPEECH_TIMEOUT) {
            serviceFailures = 0;
            scheduleListen(800);
            return;
        }
        if (code == SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS) {
            serviceFailures = MAX_SERVICE_FAILURES;
            setStatus("Mikrofon izni eksik. Android uygulama ayarlarını kontrol et.");
            return;
        }
        serviceFailures++;
        if (serviceFailures >= MAX_SERVICE_FAILURES) {
            setStatus("Ses tanıma hizmeti tekrar tekrar hata verdi (" + code
                    + "). Mikrofon veya internet hizmetini kontrol edip uygulamayı yeniden aç.");
            return;
        }
        if (code == SpeechRecognizer.ERROR_NETWORK
                || code == SpeechRecognizer.ERROR_NETWORK_TIMEOUT) {
            setStatus("Android konuşma tanıma servisi ağ hatası. Yeniden deniyorum…");
        }
        scheduleListen(1500L * serviceFailures);
    }

    private void handleUtterance(String utterance) {
        if (utterance == null || utterance.trim().isEmpty()) return;
        VoiceControl.Command command = VoiceControl.classify(utterance);
        if (command == VoiceControl.Command.MUTE) {
            voiceEnabled = false;
            if (tts != null) tts.stop();
            speaking = false;
            setStatus("SESSİZ MOD · JARVIS seni dinliyor. 'Konuş' dersen yeniden ses verir.");
            return;
        }
        if (command == VoiceControl.Command.UNMUTE) {
            boolean changed = !voiceEnabled;
            voiceEnabled = true;
            setStatus("SESLİ MOD · JARVIS konuşmaya hazır.");
            if (changed) say("Dinliyorum.", "jarvis-unmuted");
            return;
        }
        if (speaking) {
            // In speaker output, never send its echo to Gemini and create feedback loops.
            setStatus("JARVIS konuşuyor. Sesi kesmek için 'Sus' de.");
            return;
        }
        if (busy) {
            setStatus("Önceki soruyu yanıtlıyorum. 'Sus' komutu kullanılabilir.");
            return;
        }
        sendMessage(utterance);
    }

    private void append(String sender, String value) {
        String next = conversation.getText().toString() + "\n" + sender + ": " + value + "\n";
        if (next.length() > 16000) next = next.substring(next.length() - 16000);
        conversation.setText(next);
    }

    private void sendMessage(String input) {
        if (apiKey == null) {
            setStatus("Önce Gemini anahtar dosyasını seç.");
            return;
        }
        if (busy || input == null || input.trim().isEmpty()) return;
        String question = input.trim();
        if (question.length() > 2000) {
            setStatus("Soru en fazla 2000 karakter olabilir.");
            return;
        }
        String selected = String.valueOf(model.getSelectedItem());
        if (!GeminiHttp.allowedModel(selected)) {
            setStatus("Seçilen Gemini modeli desteklenmiyor.");
            return;
        }
        busy = true;
        prompt.setText("");
        append("SEN", question);
        setStatus("Gemini yanıtlıyor…");
        final String keyForCall = apiKey;
        // Snapshot the history so the background worker does not read mutable UI state.
        final JSONArray past;
        try { past = new JSONArray(history.toString()); }
        catch (Exception ignored) { busy = false; return; }
        worker.execute(() -> {
            try {
                String result = GeminiHttp.ask(keyForCall, selected, past, question);
                runOnUiThread(() -> {
                    if (destroyed) return;
                    try {
                        history.put(new JSONObject().put("role", "user").put("text", question));
                        history.put(new JSONObject().put("role", "model").put("text", result));
                        while (history.length() > 8) history.remove(0);
                    } catch (Exception ignored) { }
                    busy = false;
                    mostRecentAnswer = result;
                    append("JARVIS", result);
                    setStatus("Gemini yanıtladı · " + selected);
                    say(result.substring(0, Math.min(result.length(), 3000)), "jarvis-answer");
                    scheduleListen(400);
                });
            } catch (Exception ex) {
                final String message = ex instanceof java.io.IOException
                        ? ex.getMessage() : "Yanıt işlenemedi.";
                runOnUiThread(() -> {
                    if (destroyed) return;
                    busy = false;
                    append("JARVIS", "İstek tamamlanamadı: " + message);
                    setStatus("Gemini API bağlantısını, model erişimini ve kotanı kontrol et.");
                    scheduleListen(900);
                });
            }
        });
    }

    private static String readBounded(InputStream input, int limit) throws Exception {
        ByteArrayOutputStream result = new ByteArrayOutputStream();
        byte[] buf = new byte[1024];
        int read;
        while ((read = input.read(buf)) != -1) {
            if (result.size() + read > limit) throw new Exception("Too large");
            result.write(buf, 0, read);
        }
        return new String(result.toByteArray(), StandardCharsets.UTF_8);
    }

    @Override protected void onActivityResult(int request, int result, Intent intent) {
        super.onActivityResult(request, result, intent);
        if (request != OPEN_KEY_FILE || result != RESULT_OK
                || intent == null || intent.getData() == null) return;
        try (InputStream stream = getContentResolver().openInputStream(intent.getData())) {
            if (stream == null) throw new Exception("Missing file");
            JSONObject file = new JSONObject(readBounded(stream, 4096));
            String imported = file.optString("api_key", "");
            if (file.length() != 3 || file.optInt("version") != 2
                    || !"gemini".equals(file.optString("provider"))
                    || !imported.matches("[\\x21-\\x7e]{20,220}")) {
                throw new Exception("Invalid key file");
            }
            DeviceKeyStore.save(this, imported);
            apiKey = imported;
            keyPicker.setVisibility(Button.GONE);
            setStatus("Gemini anahtarı kaydedildi. Sesli mod başlıyor…");
            maybeGreet();
            ensureMicPermission();
        } catch (Exception e) {
            setStatus("Anahtar dosyası okunamadı. KEY-SETUP.html ile oluşturduğun jarvis-gemini-key.json'u seç.");
        }
    }

    @Override protected void onResume() {
        super.onResume();
        foreground = true;
        serviceFailures = 0;
        if (apiKey != null) {
            maybeGreet();
            ensureMicPermission();
        }
    }

    @Override protected void onStop() {
        foreground = false;
        ui.removeCallbacks(nextListen);
        releaseRecognizer();
        speaking = false;
        if (tts != null) tts.stop();
        super.onStop();
    }

    @Override protected void onDestroy() {
        destroyed = true;
        ui.removeCallbacks(nextListen);
        ui.removeCallbacks(microphoneTimeout);
        releaseRecognizer();
        if (tts != null) { tts.stop(); tts.shutdown(); }
        apiKey = null;
        worker.shutdownNow();
        super.onDestroy();
    }
}
