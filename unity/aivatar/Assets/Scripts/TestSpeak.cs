using UnityEngine;

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
