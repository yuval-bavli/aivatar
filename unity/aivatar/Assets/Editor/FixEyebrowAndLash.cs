using UnityEngine;
using UnityEditor;

/// <summary>
/// Disables the misplaced eyebrow card mesh renderer,
/// and increases eyelash _Cutoff to make them thinner.
/// </summary>
public static class FixEyebrowAndLash
{
    [MenuItem("Aivatar/Fix Eyebrow Position + Eyelash Thickness")]
    public static void Run()
    {
        int fixed_ = 0;

        // ── 1. Disable all eyebrow mesh renderers ──────────────────────────
        // The card mesh is appearing on the cheeks (wrong 3D position).
        // Disable it; we rely on the face texture painted eyebrows instead.
        var allRenderers = Resources.FindObjectsOfTypeAll<Renderer>();
        foreach (var r in allRenderers)
        {
            string name = r.gameObject.name.ToLower();
            if (name.Contains("eyebrow") || name.Contains("brow"))
            {
                if (r.enabled)
                {
                    Debug.Log($"[FixEyebrowAndLash] Disabling eyebrow renderer: {r.gameObject.name}");
                    r.enabled = false;
                    EditorUtility.SetDirty(r.gameObject);
                    fixed_++;
                }
                else
                {
                    Debug.Log($"[FixEyebrowAndLash] Already disabled: {r.gameObject.name}");
                }
            }
        }

        // ── 2. Increase eyelash _Cutoff to thin the lashes ────────────────
        string[] eyelashMats = new[] {
            "Assets/Models/Avatar/Materials/MI_Face_EyelashesHiLODs.mat",
            "Assets/Models/Avatar/Materials/AvatarEyelashes.mat",
        };

        foreach (var matPath in eyelashMats)
        {
            var mat = AssetDatabase.LoadAssetAtPath<Material>(matPath);
            if (mat == null) { Debug.LogWarning($"[FixEyebrowAndLash] Not found: {matPath}"); continue; }

            float oldCutoff = mat.GetFloat("_Cutoff");
            mat.SetFloat("_Cutoff", 0.72f);
            // Also ensure alpha clip is on
            mat.SetFloat("_AlphaClip", 1f);
            mat.EnableKeyword("_ALPHATEST_ON");
            mat.DisableKeyword("_SURFACE_TYPE_TRANSPARENT");
            mat.renderQueue = 2450;

            EditorUtility.SetDirty(mat);
            Debug.Log($"[FixEyebrowAndLash] {System.IO.Path.GetFileName(matPath)}: _Cutoff {oldCutoff} -> 0.72");
            fixed_++;
        }

        AssetDatabase.SaveAssets();
        AssetDatabase.Refresh();
        Debug.Log($"[FixEyebrowAndLash] Done. {fixed_} items changed.");
    }
}
