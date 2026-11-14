package ai.jarvis.geminitv;

import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.graphics.Color;
import android.os.Bundle;
import android.speech.RecognizerIntent;
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
    private static final int BLUE = Color.rgb(120, 220, 255);
    private final ExecutorService worker = Executors.newSingleThreadExecutor();
    private final JSONArray history = new JSONArray();
    private TextView status, transcript;
    private EditText prompt;
    private Button send;
    private Spinner model;
    private TextToSpeech tts;
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

        Button speech = button("🎤 Sesle konuş (varsa)");
        root.addView(speech);
        speech.setOnClickListener(v -> startVoice());

        Button clear = button("Sohbeti temizle");
        root.addView(clear);
        clear.setOnClickListener(v -> {
            while (history.length() > 0) history.remove(0);
            transcript.setText("JARVIS: Sohbet temizlendi.\n");
        });

        root.addView(text("USB anahtar dosyası ŞİFRESİZDİR: USB'yi bulan kişi Gemini anahtarını kullanabilir. "
                + "İçe aktarıldıktan sonra Android uygulaması anahtarı kendi Keystore şifrelemesiyle saklar. "
                + "Sesle giriş için cihazda konuşma tanıma servisi ve mikrofon gerekir. "
                + "Yanıtı sesli okuma için Android TTS gerekir. Bunlar tüm TV'lerde yoktur. "
                + "Her Gemini isteği Google'a internet üzerinden gider; anahtar kotanı/bütçeni kontrol et.",
                14, Color.LTGRAY));
        tts = new TextToSpeech(this, code -> {
            if (code == TextToSpeech.SUCCESS && tts != null) {
                int result = tts.setLanguage(new Locale("tr", "TR"));
                speakReady = result != TextToSpeech.LANG_MISSING_DATA
                        && result != TextToSpeech.LANG_NOT_SUPPORTED;
            }
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
                setStatus("Gemini anahtarı kaydedildi. Bu cihazda yeniden şifre girmen gerekmeyecek.");
            } catch (Exception ex) {
                setStatus("Anahtar içe aktarılamadı. Yeni KEY-SETUP.html ile şifresiz jarvis-gemini-key.json oluştur.");
            }
        } else if (request == VOICE_INPUT && result == RESULT_OK && data != null) {
            ArrayList<String> words = data.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS);
            if (words != null && !words.isEmpty()) {
                prompt.setText(words.get(0));
                sendMessage();
            }
        }
    }

    private void startVoice() {
        if (apiKey == null) { setStatus("Önce Gemini anahtarını USB dosyasından içe aktar."); return; }
        Intent intent = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, "tr-TR");
        intent.putExtra(RecognizerIntent.EXTRA_PROMPT, "JARVIS dinliyor…");
        try { startActivityForResult(intent, VOICE_INPUT); }
        catch (ActivityNotFoundException | SecurityException ex) {
            setStatus("Bu cihazda ses tanıma uygulaması veya mikrofon erişimi yok. Yazılı sohbeti kullan.");
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
                    if (speakReady && tts != null) {
                        tts.speak(result.substring(0, Math.min(result.length(), 3000)),
                                TextToSpeech.QUEUE_FLUSH, null, "jarvis-answer");
                    }
                });
            } catch (Exception ex) {
                // Never log API credentials, network bodies, or prompts.
                final String message = ex instanceof java.io.IOException ?
                        ex.getMessage() : "Gemini yanıtı işlenemedi.";
                runOnUiThread(() -> {
                    appendConversation("JARVIS", "İstek başarısız: " + message);
                    setStatus("Bağlantıyı, Gemini anahtarını ve kotayı kontrol et.");
                    busy = false; send.setEnabled(true);
                });
            }
        });
    }

    @Override protected void onDestroy() {
        apiKey = null;
        speakReady = false;
        if (tts != null) { tts.stop(); tts.shutdown(); }
        worker.shutdownNow();
        super.onDestroy();
    }
}
