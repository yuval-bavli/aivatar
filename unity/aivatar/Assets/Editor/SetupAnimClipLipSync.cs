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

        // Find the visible face mesh root — the root-level GameObject containing
        // a SkinnedMeshRenderer whose bone count matches viseme_animation's.
        GameObject targetRoot = null;
        int bestBoneCount = 0;
        foreach (var go in Object.FindObjectsByType<GameObject>(
            FindObjectsInactive.Include, FindObjectsSortMode.None))
        {
            if (go.transform.parent != null) continue;
            if (go == animRoot.gameObject) continue; // skip the animation source itself

            var smrs = go.GetComponentsInChildren<SkinnedMeshRenderer>(true);
            foreach (var smr in smrs)
            {
                if (smr == null || smr.bones == null) continue;
                if (smr.bones.Length > bestBoneCount)
                {
                    // Check if this SMR's bones contain facial bones (FACIAL_* or head)
                    bool hasFacial = false;
                    foreach (var b in smr.bones)
                    {
                        if (b != null && (b.name.Contains("FACIAL") || b.name == "head"))
                        { hasFacial = true; break; }
                    }
                    if (hasFacial)
                    {
                        bestBoneCount = smr.bones.Length;
                        targetRoot = go;
                    }
                }
            }
        }
        if (targetRoot != null)
            sb.AppendLine($"Visible face root: '{targetRoot.name}' (bones={bestBoneCount})");
        else
            sb.AppendLine("WARNING: no visible face root found; falling back to animRoot");

        Undo.RecordObject(lipSync, "Wire AnimClipLipSync");
        lipSync.visemeClip = clip;
        lipSync.animRoot = animRoot.gameObject;
        lipSync.targetRoot = targetRoot;
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

    /// <summary>Check if the animation clip has real facial deformation by comparing sil vs aa poses.</summary>
    public static string CheckPoses()
    {
        AnimationClip clip = null;
        foreach (var asset in AssetDatabase.LoadAllAssetsAtPath(ANIM_FBX_PATH))
            if (asset is AnimationClip c && !c.name.StartsWith("__preview__")) { clip = c; break; }
        if (clip == null) return "ERROR: no clip";

        Transform root = null;
        foreach (var go in Object.FindObjectsByType<GameObject>(FindObjectsInactive.Include, FindObjectsSortMode.None))
            if (go.name == "viseme_animation" && go.transform.parent == null) { root = go.transform; break; }
        if (root == null) return "ERROR: viseme_animation not found";

        float fps = clip.frameRate > 0 ? clip.frameRate : 30f;
        var tempClip = Object.Instantiate(clip);
        tempClip.legacy = true;

        var sb = new System.Text.StringBuilder();
        sb.AppendLine($"Clip: '{clip.name}' fps={fps} length={clip.length:F2}s frames={Mathf.RoundToInt(clip.length * fps)}");
        sb.AppendLine($"Curves: {AnimationUtility.GetCurveBindings(clip).Length} bindings");

        // Sample sil (frame 0) and aa (frame 100), compare key facial transforms
        string[] boneNames = { "head", "jaw", "FACIAL_C_FacialRoot", "FACIAL_C_Jaw", "neck_01" };
        tempClip.SampleAnimation(root.gameObject, 0f);
        var silPoses = new System.Collections.Generic.Dictionary<string, Vector3>();
        foreach (var t in root.GetComponentsInChildren<Transform>())
            if (System.Array.IndexOf(boneNames, t.name) >= 0 || t.name.Contains("jaw") || t.name.Contains("Jaw"))
                silPoses[t.name] = t.localRotation.eulerAngles;

        tempClip.SampleAnimation(root.gameObject, 100f / fps);
        sb.AppendLine("\nBone rotations sil(frame0) vs aa(frame100):");
        int changed = 0;
        foreach (var t in root.GetComponentsInChildren<Transform>())
        {
            if (silPoses.ContainsKey(t.name))
            {
                Vector3 aaPose = t.localRotation.eulerAngles;
                Vector3 diff = aaPose - silPoses[t.name];
                sb.AppendLine($"  {t.name}: sil={silPoses[t.name]:F1} aa={aaPose:F1} delta={diff.magnitude:F3}");
                if (diff.magnitude > 0.1f) changed++;
            }
        }
        sb.AppendLine($"\nBones with changed rotation: {changed}/{silPoses.Count}");

        // Also report first 5 curve bindings to see what properties are animated
        var bindings = AnimationUtility.GetCurveBindings(clip);
        sb.AppendLine($"\nFirst 10 curve bindings:");
        for (int i = 0; i < Mathf.Min(10, bindings.Length); i++)
            sb.AppendLine($"  {bindings[i].path} / {bindings[i].propertyName}");

        tempClip.SampleAnimation(root.gameObject, 0f); // reset to sil
        Object.DestroyImmediate(tempClip);
        return sb.ToString();
    }
}
#endif
