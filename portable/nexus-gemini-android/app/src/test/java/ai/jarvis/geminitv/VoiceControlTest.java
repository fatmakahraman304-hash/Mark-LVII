package ai.jarvis.geminitv;

import static org.junit.Assert.assertEquals;
import org.junit.Test;

public class VoiceControlTest {
    @Test public void muteCommandsDoNotRequireButtons() {
        assertEquals(VoiceControl.Command.MUTE, VoiceControl.classify("Sus"));
        assertEquals(VoiceControl.Command.MUTE, VoiceControl.classify("JARVIS, SUS!"));
        assertEquals(VoiceControl.Command.MUTE, VoiceControl.classify("sessiz ol"));
        assertEquals(VoiceControl.Command.MUTE, VoiceControl.classify("sesini kapat"));
    }
    @Test public void resumeSpeechWhenMuted() {
        assertEquals(VoiceControl.Command.UNMUTE, VoiceControl.classify("konuş"));
        assertEquals(VoiceControl.Command.UNMUTE, VoiceControl.classify("Jarvis konuş"));
        assertEquals(VoiceControl.Command.UNMUTE, VoiceControl.classify("Konuşmaya başla."));
        assertEquals(VoiceControl.Command.UNMUTE, VoiceControl.classify("sesini aç"));
    }
    @Test public void doNotMistakeQuestionsForCommands() {
        assertEquals(VoiceControl.Command.NONE, VoiceControl.classify("Sus ne demek?"));
        assertEquals(VoiceControl.Command.NONE, VoiceControl.classify("Herkes sus dediğinde ne olur?"));
        assertEquals(VoiceControl.Command.NONE, VoiceControl.classify("Ne zaman konuşalım?"));
        assertEquals(VoiceControl.Command.NONE, VoiceControl.classify("Merhaba JARVIS, beni duyuyor musun?"));
        assertEquals(VoiceControl.Command.NONE, VoiceControl.classify(""));
        assertEquals(VoiceControl.Command.NONE, VoiceControl.classify(null));
    }
}
