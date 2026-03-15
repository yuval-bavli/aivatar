using UnityEngine;
using UnityEditor;
using System.Text;

public static class DiagnoseEyebrowMesh
{
    public static string Run()
    {
        var sb = new StringBuilder();
        Renderer browRenderer = null;
        foreach (var r in Resources.FindObjectsOfTypeAll<Renderer>())
        {
            if (r.hideFlags != HideFlags.None) continue;
            if (r.gameObject.name.ToLower().Contains("eyebrow") || r.gameObject.name.ToLower().Contains("brow"))
            { browRenderer = r; break; }
        }
        if (browRenderer == null) return "ERROR: no eyebrow renderer";

        sb.AppendLine($"Bounds: center={browRenderer.bounds.center} size={browRenderer.bounds.size}");

        // Also get camera info
        Camera cam = Camera.main;
        if (cam == null && SceneView.lastActiveSceneView != null)
            cam = SceneView.lastActiveSceneView.camera;
        if (cam != null)
            sb.AppendLine($"Camera: pos={cam.transform.position} near={cam.nearClipPlane} far={cam.farClipPlane}");

        return sb.ToString();
    }

    // Make eyebrow material solid bright red so we can see the mesh
    public static string MakeSolid()
    {
        Renderer browRenderer = null;
        foreach (var r in Resources.FindObjectsOfTypeAll<Renderer>())
        {
            if (r.hideFlags != HideFlags.None) continue;
            if (r.gameObject.name.ToLower().Contains("eyebrow") || r.gameObject.name.ToLower().Contains("brow"))
            { browRenderer = r; break; }
        }
        if (browRenderer == null) return "ERROR: no eyebrow renderer";

        foreach (var m in browRenderer.sharedMaterials)
        {
            if (m == null) continue;
            m.SetFloat("_AlphaClip", 0f);   // disable alpha clipping
            m.DisableKeyword("_ALPHATEST_ON");
            m.SetColor("_BaseColor", Color.red);  // bright red
            m.renderQueue = 2000;
            EditorUtility.SetDirty(m);
        }
        AssetDatabase.SaveAssets();
        return $"Made solid red: {browRenderer.gameObject.name}";
    }
}
