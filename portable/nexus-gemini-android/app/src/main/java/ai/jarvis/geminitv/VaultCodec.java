package ai.jarvis.geminitv;

import android.util.Base64;
import org.json.JSONException;
import org.json.JSONObject;
import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.util.Arrays;
import javax.crypto.Cipher;
import javax.crypto.SecretKeyFactory;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.PBEKeySpec;
import javax.crypto.spec.SecretKeySpec;

/** Decrypts a USB-generated vault; no decrypted key is ever written to storage. */
public final class VaultCodec {
    private VaultCodec() {}
    public static String unlock(String encodedVault, char[] passphrase)
            throws JSONException, GeneralSecurityException {
        if (encodedVault == null || encodedVault.length() > 8192
                || passphrase == null || passphrase.length < 10 || passphrase.length > 100) {
            throw new GeneralSecurityException("Invalid vault or password");
        }
        JSONObject vault = new JSONObject(encodedVault);
        if (vault.length() != 6 || vault.getInt("version") != 1
                || !"PBKDF2-SHA256".equals(vault.getString("kdf"))
                || vault.getInt("iterations") != 250000) {
            throw new GeneralSecurityException("Unsupported vault format");
        }
        byte[] salt = Base64.decode(vault.getString("salt"), Base64.DEFAULT);
        byte[] nonce = Base64.decode(vault.getString("iv"), Base64.DEFAULT);
        byte[] encrypted = Base64.decode(vault.getString("ciphertext"), Base64.DEFAULT);
        if (salt.length != 16 || nonce.length != 12 || encrypted.length < 36
                || encrypted.length > 1024) {
            throw new GeneralSecurityException("Invalid vault sizes");
        }
        PBEKeySpec spec = new PBEKeySpec(passphrase, salt, 250000, 256);
        byte[] key = null;
        byte[] plain = null;
        try {
            key = SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256")
                    .generateSecret(spec).getEncoded();
            Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
            cipher.init(Cipher.DECRYPT_MODE, new SecretKeySpec(key, "AES"),
                    new GCMParameterSpec(128, nonce));
            plain = cipher.doFinal(encrypted);
            String result = new String(plain, StandardCharsets.UTF_8);
            if (!result.matches("[\\x21-\\x7e]{20,220}")) {
                throw new GeneralSecurityException("Invalid decrypted key format");
            }
            return result;
        } finally {
            spec.clearPassword();
            if (plain != null) Arrays.fill(plain, (byte) 0);
            if (key != null) Arrays.fill(key, (byte) 0);
            Arrays.fill(salt, (byte) 0);
            Arrays.fill(encrypted, (byte) 0);
        }
    }
}
