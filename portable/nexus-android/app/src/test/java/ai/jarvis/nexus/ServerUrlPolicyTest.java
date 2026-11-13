package ai.jarvis.nexus;

import org.junit.Test;
import static org.junit.Assert.*;

public class ServerUrlPolicyTest {
    @Test public void acceptsHttpsOrigin() throws Exception {
        assertEquals("https://example.com:8765", ServerUrlPolicy.normalize(" https://EXAMPLE.com:8765/ "));
    }
    @Test public void rejectsUntrustedInputs() {
        String[] bad = {"http://example.com", "https://a.test/path", "https://user:pass@a.test",
            "https://a.test/?token=abc", "https://a.test/#fragment", "javascript:alert(1)",
            "https://a.test:0", "https://a.test:65536", ""};
        for (String value : bad) {
            try { ServerUrlPolicy.normalize(value); fail("Accepted: " + value); }
            catch (java.net.URISyntaxException expected) {}
        }
    }
    @Test public void checksSameOrigin() {
        assertTrue(ServerUrlPolicy.sameOrigin("https://example.com:8765", "https://EXAMPLE.com:8765/app"));
        assertFalse(ServerUrlPolicy.sameOrigin("https://example.com:8765", "https://example.com/app"));
        assertFalse(ServerUrlPolicy.sameOrigin("https://example.com", "https://evil.test/"));
        assertFalse(ServerUrlPolicy.sameOrigin("https://example.com", "http://example.com/"));
        assertFalse(ServerUrlPolicy.sameOrigin("https://example.com", "https://user@example.com/"));
    }
}
