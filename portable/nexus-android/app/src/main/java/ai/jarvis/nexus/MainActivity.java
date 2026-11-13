package ai.jarvis.nexus;

import android.app.Activity;
import android.os.Bundle;
import android.graphics.Color;
import android.view.View;
import android.view.ViewGroup;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebChromeClient;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.net.Uri;
import android.content.Intent;
import android.text.InputType;

/** User-authorized HTTPS-only JARVIS client. No JavaScript bridge or silent installation. */
public final class MainActivity extends Activity {
    private WebView web;
    private String trustedOrigin;
    private LinearLayout root;
    private TextView status;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(20, 20, 20, 20);
        root.setBackgroundColor(Color.rgb(7, 18, 31));
        setContentView(root);
        showSetup();
    }

    private TextView label(String text) {
        TextView t = new TextView(this);
        t.setText(text);
        t.setTextSize(19);
        t.setTextColor(Color.WHITE);
        t.setPadding(0, 12, 0, 12);
        return t;
    }

    private void showSetup() {
        if (web != null) { root.removeView(web); web.destroy(); web = null; }
        root.removeAllViews();
        root.addView(label("JARVIS NEXUS • Wi-Fi istemcisi"));
        root.addView(label("Güvendiğiniz JARVIS sunucusunun HTTPS adresini girin. Sertifika doğrulaması zorunludur."));
        EditText address = new EditText(this);
        address.setSingleLine(true);
        address.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_URI);
        address.setHint("https://192.168.1.10:8765");
        address.setTextColor(Color.WHITE);
        address.setHintTextColor(Color.LTGRAY);
        root.addView(address);
        status = label("Hazır. Henüz bağlantı kurulmadı.");
        Button connect = new Button(this);
        connect.setText("JARVIS'i aç");
        root.addView(connect);
        root.addView(status);
        connect.setOnClickListener(v -> {
            try {
                trustedOrigin = ServerUrlPolicy.normalize(address.getText().toString());
                showBrowser();
            } catch (Exception e) {
                status.setText("Geçersiz adres.");
            }
        });
    }

    private boolean sameOrigin(Uri uri) {
        return uri != null && ServerUrlPolicy.sameOrigin(trustedOrigin, uri.toString());
    }

    private void showBrowser() {
        root.removeAllViews();
        Button disconnect = new Button(this);
        disconnect.setText("Oturumu kapat / Geri");
        root.addView(disconnect);
        web = new WebView(this);
        web.getSettings().setJavaScriptEnabled(true);
        web.getSettings().setDomStorageEnabled(true);
        web.getSettings().setAllowFileAccess(false);
        web.getSettings().setAllowContentAccess(false);
        web.getSettings().setJavaScriptCanOpenWindowsAutomatically(false);
        web.getSettings().setMixedContentMode(android.webkit.WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        web.setWebChromeClient(new WebChromeClient());
        web.setWebViewClient(new WebViewClient() {
            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                if (sameOrigin(request.getUrl())) return false;
                // Do not silently send user/session data to external destinations.
                return true;
            }
            @Override public void onReceivedSslError(WebView view,
                    android.webkit.SslErrorHandler handler, android.net.http.SslError error) {
                handler.cancel(); // Never bypass certificate errors.
            }
        });
        root.addView(web, new LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, 0, 1));
        disconnect.setOnClickListener(v -> {
            web.stopLoading();
            web.clearHistory();
            web.clearCache(true);
            android.webkit.CookieManager.getInstance().removeAllCookies(null);
            android.webkit.CookieManager.getInstance().flush();
            trustedOrigin = null;
            showSetup();
        });
        web.loadUrl(trustedOrigin + "/");
    }

    @Override public void onBackPressed() {
        if (web != null) { trustedOrigin = null; showSetup(); }
        else super.onBackPressed();
    }

    @Override protected void onDestroy() {
        if (web != null) { web.destroy(); web = null; }
        super.onDestroy();
    }
}
