using UnityEngine;
using UnityEditor;

public static class ToggleEyebrowRenderer
{
    public static string Disable()
    {
        foreach (var r in Resources.FindObjectsOfTypeAll<Renderer>())
        {
            if (r.hideFlags != HideFlags.None) continue;
            if (r.gameObject.name.ToLower().Contains("eyebrow") || r.gameObject.name.ToLower().Contains("brow"))
            {
                r.enabled = false;
                EditorUtility.SetDirty(r.gameObject);
                return $"Disabled: {r.gameObject.name}";
            }
        }
        return "ERROR: no brow renderer";
    }

    public static string Enable()
    {
        foreach (var r in Resources.FindObjectsOfTypeAll<Renderer>())
        {
            if (r.hideFlags != HideFlags.None) continue;
            if (r.gameObject.name.ToLower().Contains("eyebrow") || r.gameObject.name.ToLower().Contains("brow"))
            {
                r.enabled = true;
                EditorUtility.SetDirty(r.gameObject);
                return $"Enabled: {r.gameObject.name}";
            }
        }
        return "ERROR: no brow renderer";
    }
}
