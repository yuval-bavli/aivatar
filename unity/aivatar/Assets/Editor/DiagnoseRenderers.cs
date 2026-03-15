using UnityEngine;
using UnityEditor;

public static class DiagnoseRenderers
{
    [MenuItem("Aivatar/Diagnose All Renderers")]
    public static void Run()
    {
        // Find ALL renderers in open scenes including inactive objects
        var renderers = Resources.FindObjectsOfTypeAll<Renderer>();
        Debug.Log($"[Diagnose] Total renderers found: {renderers.Length}");
        foreach (var r in renderers)
        {
            // Skip built-in/hidden objects
            if (r.hideFlags != HideFlags.None) continue;
            string mats = "";
            foreach (var m in r.sharedMaterials)
                mats += (m != null ? m.name : "null") + ",";
            Debug.Log($"[Diagnose] name={r.gameObject.name} | enabled={r.enabled} | type={r.GetType().Name} | mats=[{mats}]");
        }
    }

    [MenuItem("Aivatar/Disable Eyebrow Renderers (All Methods)")]
    public static void DisableEyebrows()
    {
        int count = 0;
        var renderers = Resources.FindObjectsOfTypeAll<Renderer>();
        foreach (var r in renderers)
        {
            if (r.hideFlags != HideFlags.None) continue;
            string lower = r.gameObject.name.ToLower();
            bool hasBrowMat = false;
            foreach (var m in r.sharedMaterials)
                if (m != null && m.name.ToLower().Contains("brow")) { hasBrowMat = true; break; }

            if (lower.Contains("brow") || lower.Contains("eyebrow") || hasBrowMat)
            {
                Debug.Log($"[DisableEyebrows] Disabling: {r.gameObject.name} (enabled was {r.enabled})");
                r.enabled = false;
                r.gameObject.SetActive(false);
                EditorUtility.SetDirty(r.gameObject);
                count++;
            }
        }
        AssetDatabase.SaveAssets();
        Debug.Log($"[DisableEyebrows] Disabled {count} eyebrow renderers.");
    }
}
