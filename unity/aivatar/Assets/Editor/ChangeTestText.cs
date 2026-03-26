using UnityEngine;
using UnityEditor;

public class ChangeTestText
{
    public static string Run()
    {
        var ts = Object.FindFirstObjectByType<TestSpeak>();
        if (ts == null) return "ERROR: TestSpeak not found";

        // Sentence designed to clearly show each viseme:
        // "Papa" = PP viseme (lips pressed)
        // "fish" = FF + ih + SS/CH visemes
        // "tooth" = TH viseme (tongue)
        // "shoe" = CH + ou visemes (pucker)
        // "boo" = PP + ou (lips round)
        // "ahh" = aa (wide open)
        // "oh no" = oh + nn + oh
        // "see" = SS + ih (spread)
        ts.testText = "Oh, Oh, Oh, Oh, Oh.";

        EditorUtility.SetDirty(ts);
        UnityEditor.SceneManagement.EditorSceneManager.SaveOpenScenes();
        return $"Test text set to: {ts.testText}";
    }
}
