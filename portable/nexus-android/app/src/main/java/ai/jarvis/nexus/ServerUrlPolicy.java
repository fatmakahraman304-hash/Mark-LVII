package ai.jarvis.nexus;

import java.net.URI;
import java.net.URISyntaxException;
import java.util.Locale;

/** Pure-Java URL policy: no credentials, redirects to new origins, or cleartext. */
public final class ServerUrlPolicy {
    private ServerUrlPolicy() {}

    public static String normalize(String input) throws URISyntaxException {
        if (input == null) throw new URISyntaxException("", "Missing URL");
        URI uri = new URI(input.trim());
        if (!"https".equalsIgnoreCase(uri.getScheme()) ||
            uri.getHost() == null || uri.getHost().isEmpty() ||
            uri.getRawUserInfo() != null || uri.getRawQuery() != null ||
            uri.getRawFragment() != null ||
            (uri.getRawPath() != null && !uri.getRawPath().isEmpty() && !"/".equals(uri.getRawPath())) ||
            uri.getPort() > 65535 || uri.getPort() == 0 ||
            uri.getPort() < -1) {
            throw new URISyntaxException(input, "Expected HTTPS server root URL");
        }
        String host = uri.getHost().toLowerCase(Locale.ROOT);
        if (host.indexOf(':') >= 0) host = "[" + host + "]";
        return "https://" + host + (uri.getPort() == -1 ? "" : ":" + uri.getPort());
    }

    public static boolean sameOrigin(String trustedOrigin, String target) {
        try {
            if (trustedOrigin == null || target == null) return false;
            URI uri = new URI(target);
            if (!"https".equalsIgnoreCase(uri.getScheme()) ||
                uri.getHost() == null || uri.getRawUserInfo() != null) return false;
            return normalize(trustedOrigin).equals(
                "https://" + (uri.getHost().contains(":") ? "[" + uri.getHost().toLowerCase(Locale.ROOT) + "]" :
                uri.getHost().toLowerCase(Locale.ROOT)) + (uri.getPort() == -1 ? "" : ":" + uri.getPort()));
        } catch (Exception e) { return false; }
    }
}
