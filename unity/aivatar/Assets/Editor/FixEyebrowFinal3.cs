using UnityEngine;
using UnityEditor;

public static class FixEyebrowFinal3
{
    [MenuItem("Aivatar/Fix Eyebrow Final3")]
    public static string Run()
    {
        var log = new System.Text.StringBuilder();

        var browGO = FindRendererByName("Eyebrows_M_Natural_CardsMesh_Group0_LOD0");
        if (browGO == null) return "ERROR: not found";

        // Push more forward (local -Y) to clear brow ridge depth
        // -0.08 should be ~8cm forward, clearing the nose/brow ridge
        browGO.transform.localPosition = new Vector3(-0.01f, -0.08f, -0.76f);
        EditorUtility.SetDirty(browGO);

        var browRenderer = browGO.GetComponent<Renderer>();
        log.AppendLine($"Eyebrow world bounds: center={browRenderer.bounds.center}");

        // Still red for testing
        AssetDatabase.SaveAssets();
        return log.ToString();
    }

    static GameObject FindRendererByName(string name)
    {
        foreach (var r in Object.FindObjectsOfType<Renderer>())
            if (r.gameObject.name == name) return r.gameObject;
        return null;
    }
}
