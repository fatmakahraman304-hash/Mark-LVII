package ai.jarvis.geminitv;

import android.content.Context;
import android.content.SharedPreferences;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;
import android.util.Base64;
import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.security.KeyStore;
import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;

/**
 * Passwordless, on-device encrypted storage for a Gemini API key.
 * The removable USB JSON is plaintext; ONLY the installed Android app uses
 * Android Keystore protection. No key bytes or values are logged.
 * App reinstall or clearing app data invalidates the stored key.
 */
public final class DeviceKeyStore {
    private static final String ALIAS = "jarvis_gemini_v2";
    private static final String PREFS = "jarvis_gemini_secure_v2";
    private static final String IV_NAME = "iv";
    private static final String CT_NAME = "ciphertext";

    private DeviceKeyStore() {}

    private static KeyStore store() throws Exception {
        KeyStore ks = KeyStore.getInstance("AndroidKeyStore");
        ks.load(null);
        return ks;
    }

    private static SecretKey key(boolean create) throws Exception {
        KeyStore ks = store();
        SecretKey result = (SecretKey) ks.getKey(ALIAS, null);
        if (result != null || !create) return result;
        KeyGenerator generator = KeyGenerator.getInstance(
                KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore");
        generator.init(new KeyGenParameterSpec.Builder(
                ALIAS, KeyProperties.PURPOSE_ENCRYPT | KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setKeySize(256)
                .setRandomizedEncryptionRequired(true)
                .build());
        return generator.generateKey();
    }

    public static void save(Context context, String apiKey) throws Exception {
        if (apiKey == null || !apiKey.matches("[\\x21-\\x7e]{20,220}")) {
            throw new GeneralSecurityException("Invalid API key");
        }
        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.ENCRYPT_MODE, key(true));
        byte[] encrypted = cipher.doFinal(apiKey.getBytes(StandardCharsets.UTF_8));
        boolean ok = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit()
                .putString(IV_NAME, Base64.encodeToString(cipher.getIV(), Base64.NO_WRAP))
                .putString(CT_NAME, Base64.encodeToString(encrypted, Base64.NO_WRAP))
                .commit();
        if (!ok) throw new GeneralSecurityException("Unable to save API key");
    }

    public static String load(Context context) throws Exception {
        SharedPreferences prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
        String iv = prefs.getString(IV_NAME, null);
        String ciphertext = prefs.getString(CT_NAME, null);
        if (iv == null || ciphertext == null) return null;
        if (iv.length() > 80 || ciphertext.length() > 1024)
            throw new GeneralSecurityException("Corrupt key storage");
        SecretKey key = key(false);
        if (key == null) throw new GeneralSecurityException("Missing Android Keystore entry");
        byte[] nonce = Base64.decode(iv, Base64.NO_WRAP);
        byte[] encrypted = Base64.decode(ciphertext, Base64.NO_WRAP);
        if (nonce.length != 12 || encrypted.length < 36 || encrypted.length > 512)
            throw new GeneralSecurityException("Corrupt key storage");
        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.DECRYPT_MODE, key, new GCMParameterSpec(128, nonce));
        String result = new String(cipher.doFinal(encrypted), StandardCharsets.UTF_8);
        if (!result.matches("[\\x21-\\x7e]{20,220}"))
            throw new GeneralSecurityException("Invalid stored key");
        return result;
    }
}
