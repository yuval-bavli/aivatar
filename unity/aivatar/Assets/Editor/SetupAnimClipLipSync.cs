#if UNITY_EDITOR
using UnityEditor;
using UnityEngine;

/// <summary>
/// Wires up AnimClipLipSync: assigns the animation clip from viseme_animation.fbx,
/// sets the animRoot, and connects to AzureSpeechManager.
/// </summary>
public static class SetupAnimClipLipSync
{
    private static readonly string ANIM_FBX_PATH = "Assets/Models/Avatar/viseme_animation.fbx";

    [MenuItem("Aivatar/Setup AnimClip LipSync")]
    public static void Setup()
    {
        var result = Run();
        Debug.Log(result);
    }

    public static string Run()
    {
        var sb = new System.Text.StringBuilder();

        // 1. Load animation clip from FBX
        AnimationClip clip = null;
        foreach (var asset in AssetDatabase.LoadAllAssetsAtPath(ANIM_FBX_PATH))
        {
            if (asset is AnimationClip c && !c.name.StartsWith("__preview__"))
            {
                clip = c;
                break;
            }
        }
        if (clip == null) return "ERROR: No AnimationClip in viseme_animation.fbx";
        sb.AppendLine($"Clip: '{clip.name}' fps={clip.frameRate} length={clip.length:F2}s");

        // 2. Find viseme_animation root in scene
        Transform animRoot = null;
        foreach (var go in Object.FindObjectsByType<GameObject>(
            FindObjectsInactive.Include, FindObjectsSortMode.None))
        {
            if (go.name == "viseme_animation" && go.transform.parent == null)
            {
                animRoot = go.transform;
                break;
            }
        }
        if (animRoot == null) return "ERROR: viseme_animation not found in scene";
        sb.AppendLine($"Root: '{animRoot.name}'");

        // 3. Reset bones to rest pose using the animation
        var tempClip = Object.Instantiate(clip);
        tempClip.legacy = true;
        tempClip.SampleAnimation(animRoot.gameObject, 0f);
        Object.DestroyImmediate(tempClip);
        sb.AppendLine("Reset to rest pose");

        // 4. Wire on Avatar
        var avatarGO = GameObject.Find("Avatar");
        if (avatarGO == null) return sb + "\nERROR: Avatar not found";

        // Remove old lip sync components
        foreach (var old in avatarGO.GetComponents<LipSyncBase>())
            Undo.DestroyObjectImmediate(old);

        var lipSync = avatarGO.GetComponent<AnimClipLipSync>();
        if (lipSync == null)
            lipSync = Undo.AddComponent<AnimClipLipSync>(avatarGO);

        Undo.RecordObject(lipSync, "Wire AnimClipLipSync");
        lipSync.visemeClip = clip;
        lipSync.animRoot = animRoot.gameObject;
        EditorUtility.SetDirty(lipSync);

        var speech = avatarGO.GetComponent<AzureSpeechManager>();
        if (speech != null)
        {
            Undo.RecordObject(speech, "Wire speech");
            speech.lipSyncController = lipSync;
            EditorUtility.SetDirty(speech);
            sb.AppendLine("Wired AzureSpeechManager.lipSyncController");
        }

        sb.AppendLine("Done! AnimClipLipSync ready on Avatar.");
        return sb.ToString();
    }

    /// <summary>
    /// Quick test: sample a specific viseme frame and take screenshot.
    /// </summary>
    public static string TestViseme(int visemeId)
    {
        int[] frames = { 0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140 };
        string[] names = { "sil", "PP", "FF", "TH", "DD", "kk", "CH", "SS", "nn", "RR", "aa", "E", "ih", "oh", "ou" };

        if (visemeId < 0 || visemeId >= frames.Length) return "Invalid visemeId";

        AnimationClip clip = null;
        foreach (var asset in AssetDatabase.LoadAllAssetsAtPath(ANIM_FBX_PATH))
        {
            if (asset is AnimationClip c && !c.name.StartsWith("__preview__"))
            { clip = c; break; }
        }
        if (clip == null) return "ERROR: no clip";

        Transform root = null;
        foreach (var go in Object.FindObjectsByType<GameObject>(
            FindObjectsInactive.Include, FindObjectsSortMode.None))
        {
            if (go.name == "viseme_animation" && go.transform.parent == null)
            { root = go.transform; break; }
        }
        if (root == null) return "ERROR: no root";

        float fps = clip.frameRate > 0 ? clip.frameRate : 30f;
        var tempClip = Object.Instantiate(clip);
        tempClip.legacy = true;
        tempClip.SampleAnimation(root.gameObject, frames[visemeId] / fps);
        Object.DestroyImmediate(tempClip);

        SceneView.RepaintAll();
        return $"Sampled viseme {visemeId} ({names[visemeId]}) at frame {frames[visemeId]}";
    }

    public static string TestSil() { return TestViseme(0); }
    public static string TestAA() { return TestViseme(10); }
    public static string TestTH() { return TestViseme(3); }
    public static string TestOH() { return TestViseme(13); }
    public static string TestOU() { return TestViseme(14); }
}
#endif
