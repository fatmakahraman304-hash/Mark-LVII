package ai.jarvis.geminitv;

import java.util.Locale;

/** Exact, conservative Turkish voice commands: never send these to Gemini. */
public final class VoiceControl {
    public enum Command { NONE, MUTE, UNMUTE }
    private VoiceControl() {}

    public static Command classify(String utterance) {
        if (utterance == null) return Command.NONE;
        String cmd = utterance.toLowerCase(Locale.ROOT).replace("\u0307", "")
                .replaceAll("[^\\p{L}\\p{N}\\s]", " ")
                .replaceAll("\\s+", " ").trim();
        switch (cmd) {
            case "sus":
            case "jarvis sus":
            case "sessiz ol":
            case "jarvis sessiz ol":
            case "sesini kapat":
            case "jarvis sesini kapat":
                return Command.MUTE;
            case "konuş":
            case "jarvis konuş":
            case "konuşmaya başla":
            case "jarvis konuşmaya başla":
            case "sesini aç":
            case "jarvis sesini aç":
                return Command.UNMUTE;
            default:
                return Command.NONE;
        }
    }
}
