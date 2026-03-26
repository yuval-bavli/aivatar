#if UNITY_EDITOR
using UnityEditor;
using UnityEngine;

public static class CheckSceneSetup
{
    public static string Run()
    {
        var sb = new System.Text.StringBuilder();
        var avatar = GameObject.Find("Avatar");
        if (avatar == null) return "ERROR: Avatar not found";

        var speech = avatar.GetComponent<AzureSpeechManager>();
        sb.AppendLine($"AzureSpeechManager: {(speech != null ? "YES" : "MISSING")}");
        if (speech != null)
            sb.AppendLine($"  lipSyncController: {speech.lipSyncController?.GetType().Name ?? "NULL"}");

        var animLip = avatar.GetComponent<AnimClipLipSync>();
        if (animLip != null)
        {
            sb.AppendLine($"AnimClipLipSync: clip={animLip.visemeClip?.name ?? "NULL"} root={animLip.animRoot?.name ?? "NULL"}");
        }

        return sb.ToString();
    }

    public static string AddTestSpeak()
    {
        var avatar = GameObject.Find("Avatar");
        if (avatar == null) return "ERROR: Avatar not found";

        var speech = avatar.GetComponent<AzureSpeechManager>();
        if (speech == null) return "ERROR: AzureSpeechManager not found on Avatar";

        var testSpeak = avatar.GetComponent<TestSpeak>();
        if (testSpeak == null)
            testSpeak = Undo.AddComponent<TestSpeak>(avatar);

        Undo.RecordObject(testSpeak, "Wire TestSpeak");
        testSpeak.speechManager = speech;
        testSpeak.testText = "Hello, I am your AI avatar. How are you doing today?";
        EditorUtility.SetDirty(testSpeak);

        return $"Added TestSpeak to Avatar. Text: \"{testSpeak.testText}\"";
    }
}
#endif
