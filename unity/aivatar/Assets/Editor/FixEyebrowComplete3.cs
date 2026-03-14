using UnityEngine;
using UnityEditor;

public static class FixEyebrowComplete3
{
    [MenuItem("Aivatar/Fix Eyebrow Complete3")]
    public static string Run()
    {
        var log = new System.Text.StringBuilder();

        Renderer browRenderer = null;
        foreach (var r in Object.FindObjectsOfType<Renderer>(true))
            if (r.gameObject.name == "Eyebrows_M_Natural_CardsMesh_Group0_LOD0")
            { browRenderer = r; break; }
        if (browRenderer == null) return "ERROR: not found";

        browRenderer.enabled = true;
        var browGO = browRenderer.gameObject;

        // Try local Z = -0.775 (between forehead at -0.76 and cheeks at -0.81)
        browGO.transform.localPosition = new Vector3(-0.01f, -0.035f, -0.765f);
        EditorUtility.SetDirty(browGO);

        log.AppendLine($"Eyebrow world bounds: center={browRenderer.bounds.center}");

        AssetDatabase.SaveAssets();
        return log.ToString();
    }
}
