#if UNITY_EDITOR
using UnityEditor;
using UnityEngine;

/// <summary>Agent bridge helper: enters Play mode so TestSpeak.Start() fires.</summary>
public static class AgentSpeak
{
    /// <summary>Text to pass when SpeakText.Run() is called.</summary>
    public static string pendingText = "thank you very much";

    public static string Run()
    {
        if (EditorApplication.isPlaying)
            return "Already in Play mode";

        EditorApplication.isPlaying = true;
        return "Entering Play mode";
    }

    public static string Stop()
    {
        if (!EditorApplication.isPlaying)
            return "Not in Play mode";

        EditorApplication.isPlaying = false;
        return "Exiting Play mode";
    }

    /// <summary>Trigger speech while already in play mode, using AzureSpeechManager in the scene.</summary>
    public static string SpeakThankYou()
    {
        if (!Application.isPlaying)
            return "ERROR: not in play mode";

        var mgr = Object.FindObjectOfType<AzureSpeechManager>();
        if (mgr == null)
            return "ERROR: AzureSpeechManager not found";

        mgr.Speak("thank you very much");
        return $"OK: Speak called on {mgr.gameObject.name}";
    }
}
#endif
