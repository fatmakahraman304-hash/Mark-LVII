package ai.jarvis.geminitv;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;

/** HTTPS-only Gemini generateContent; never routes to paid third-party models. */
public final class GeminiHttp {
    private GeminiHttp() {}
    public static final String[] MODELS = {
            "gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-3.8-flash"
    };
    public static boolean allowedModel(String model) {
        for (String allowed : MODELS) if (allowed.equals(model)) return true;
        return false;
    }
    public static String ask(String key, String model, JSONArray previous, String prompt)
            throws IOException, JSONException {
        if (key == null || !key.matches("[\\x21-\\x7e]{20,220}")
                || !allowedModel(model) || prompt == null
                || prompt.trim().isEmpty() || prompt.length() > 2000) {
            throw new IOException("Invalid request");
        }
        JSONArray contents = new JSONArray();
        int start = Math.max(0, previous.length() - 8);
        for (int i = start; i < previous.length(); i++) {
            JSONObject history = previous.getJSONObject(i);
            String role = history.optString("role", "");
            String text = history.optString("text", "");
            if ((!"user".equals(role) && !"model".equals(role))
                    || text.length() > 3000) continue;
            contents.put(new JSONObject().put("role", role)
                    .put("parts", new JSONArray().put(new JSONObject().put("text", text))));
        }
        contents.put(new JSONObject().put("role", "user")
                .put("parts", new JSONArray().put(new JSONObject().put("text", prompt.trim()))));
        JSONObject body = new JSONObject().put("contents", contents)
                .put("generationConfig", new JSONObject().put("maxOutputTokens", 1200))
                .put("systemInstruction", new JSONObject()
                        .put("parts", new JSONArray().put(new JSONObject().put("text",
                                "Sen J.A.R.V.I.S. adlı Türkçe konuşan bir yardımcı asistansın. "
                                + "Cihaz kontrolü veya veri erişimi yapabildiğini iddia etme."))));
        HttpURLConnection conn = (HttpURLConnection) new URL(
                "https://generativelanguage.googleapis.com/v1beta/models/"
                + model + ":generateContent").openConnection();
        conn.setRequestMethod("POST");
        conn.setConnectTimeout(15000);
        conn.setReadTimeout(70000);
        conn.setInstanceFollowRedirects(false);
        conn.setRequestProperty("Content-Type", "application/json; charset=utf-8");
        conn.setRequestProperty("X-goog-api-key", key);
        conn.setRequestProperty("Accept", "application/json");
        conn.setDoOutput(true);
        byte[] payload = body.toString().getBytes(StandardCharsets.UTF_8);
        if (payload.length > 30000) throw new IOException("Request too large");
        try {
            try (OutputStream output = conn.getOutputStream()) {
                output.write(payload);
            }
            int code = conn.getResponseCode();
            if (code == 401 || code == 403) throw new IOException("Gemini anahtarı kabul edilmedi.");
            if (code == 429) throw new IOException("Gemini kota veya hız sınırına ulaşıldı.");
            if (code != 200) throw new IOException("Gemini HTTP " + code + " yanıtı verdi.");
            byte[] bytes;
            try (InputStream input = conn.getInputStream()) {
                ByteArrayOutputStream out = new ByteArrayOutputStream();
                byte[] buffer = new byte[4096];
                int n;
                while ((n = input.read(buffer)) != -1) {
                    if (out.size() + n > 1024 * 1024) throw new IOException("Answer too large");
                    out.write(buffer, 0, n);
                }
                bytes = out.toByteArray();
            }
            JSONObject parsed = new JSONObject(new String(bytes, StandardCharsets.UTF_8));
            JSONArray candidates = parsed.optJSONArray("candidates");
            if (candidates == null || candidates.length() < 1)
                throw new IOException("Gemini bu isteğe yanıt vermedi.");
            JSONObject first = candidates.getJSONObject(0).optJSONObject("content");
            JSONArray parts = first == null ? null : first.optJSONArray("parts");
            if (parts == null) throw new IOException("Gemini yanıtı boş.");
            StringBuilder answer = new StringBuilder();
            for (int i = 0; i < parts.length(); i++) {
                String text = parts.getJSONObject(i).optString("text", "");
                if (!text.isEmpty()) answer.append(text);
            }
            if (answer.length() == 0) throw new IOException("Gemini yanıtı boş.");
            return answer.substring(0, Math.min(answer.length(), 8000));
        } finally {
            conn.disconnect();
        }
    }
}
