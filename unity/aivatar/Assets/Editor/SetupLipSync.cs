#if UNITY_EDITOR
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

public static class SetupLipSync
{
    const string VISEME_FBX = "Assets/Models/Avatar/viseme_animation.fbx";

    [MenuItem("Aivatar/Restore AnimClipLipSync")]
    public static void Restore()
    {
        // Find the Avatar GameObject (has AudioSource + lip-sync component)
        var avatarGO = GameObject.Find("Avatar");
        if (avatarGO == null) { Debug.LogError("[Restore] Avatar not found"); return; }

        // Find the viseme_animation root (pose source AND visible model)
        var visemeRoot = GameObject.Find("viseme_animation");
        if (visemeRoot == null) { Debug.LogError("[Restore] viseme_animation GameObject not found"); return; }

        // Load AnimationClip from the FBX — pick the first clip found
        var subAssets = AssetDatabase.LoadAllAssetsAtPath(VISEME_FBX);
        AnimationClip visemeClip = null;
        foreach (var a in subAssets)
        {
            var clip = a as AnimationClip;
            if (clip == null) continue;
            // Skip Unity's auto-generated preview clip
            if ((clip.hideFlags & HideFlags.NotEditable) != 0 && clip.name.StartsWith("__")) continue;
            Debug.Log("[Restore] Found clip: " + clip.name + " length=" + clip.length.ToString("F2") + "s frameRate=" + clip.frameRate);
            if (visemeClip == null) visemeClip = clip;
        }
        if (visemeClip == null) { Debug.LogError("[Restore] No AnimationClip found in " + VISEME_FBX); return; }

        // Remove ProLipSync if present
        var oldLipSync = avatarGO.GetComponent<ProLipSync>();
        if (oldLipSync != null)
        {
            Object.DestroyImmediate(oldLipSync);
            Debug.Log("[Restore] Removed ProLipSync");
        }

        // Add AnimClipLipSync (or reuse existing)
        var lipSync = avatarGO.GetComponent<AnimClipLipSync>();
        if (lipSync == null)
        {
            lipSync = avatarGO.AddComponent<AnimClipLipSync>();
            Debug.Log("[Restore] Added AnimClipLipSync");
        }

        lipSync.visemeClip = visemeClip;
        lipSync.animRoot = visemeRoot;
        lipSync.targetRoot = null; // same model for pose source + visible
        EditorUtility.SetDirty(lipSync);

        // Update ConversationClient reference to point at the new component
        var conv = GameObject.Find("ConversationManager")?.GetComponent<ConversationClient>();
        if (conv != null)
        {
            conv.lipSyncController = lipSync;
            EditorUtility.SetDirty(conv);
            Debug.Log("[Restore] Updated ConversationClient.lipSyncController");
        }
        else Debug.LogWarning("[Restore] ConversationClient not found — wire lipSyncController manually");

        // Update legacy AzureSpeechManager reference too (for the smoke-test path)
        var azure = avatarGO.GetComponent<AzureSpeechManager>();
        if (azure != null)
        {
            azure.lipSyncController = lipSync;
            EditorUtility.SetDirty(azure);
            Debug.Log("[Restore] Updated AzureSpeechManager.lipSyncController");
        }

        EditorSceneManager.MarkSceneDirty(EditorSceneManager.GetActiveScene());
        EditorSceneManager.SaveScene(EditorSceneManager.GetActiveScene());
        Debug.Log("[Restore] Done. AnimClipLipSync wired — visemeClip=" + visemeClip.name
                  + " animRoot=" + visemeRoot.name);
    }
}
#endif
