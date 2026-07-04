using UnityEngine;

// Legacy Azure-only smoke test: fires a single Speak() call via AzureSpeechManager on Start().
// Not wired into the production scene by SetupAvatarScene — add manually for a quick
// direct-TTS test that bypasses the orchestrator/STT/Claude pipeline entirely.
public class TestSpeak : MonoBehaviour
{
    public AzureSpeechManager speechManager;

    [TextArea(2, 6)]
    public string testText = "Hello, I am Shmontzka";

    void Start()
    {
        if (speechManager == null)
        {
            Debug.LogError("[TestSpeak] speechManager is not assigned.");
            return;
        }

        Debug.Log("[TestSpeak] Calling Speak()...");
        speechManager.Speak(testText);
    }
}
