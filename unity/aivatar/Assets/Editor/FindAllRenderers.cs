
using UnityEngine;
using UnityEditor;

public static class FindAllRenderers
{
    [MenuItem("Aivatar/Find All Renderers")]
    public static string Run()
    {
        var log = new System.Text.StringBuilder();
        
        // Find MeshRenderers too
        var meshR = Object.FindObjectsOfType<MeshRenderer>(true);
        log.AppendLine("MeshRenderers (" + meshR.Length + "):");
        foreach (var r in meshR)
            log.AppendLine("  " + r.gameObject.name + " active=" + r.gameObject.activeInHierarchy + " enabled=" + r.enabled);

        var skmR = Object.FindObjectsOfType<SkinnedMeshRenderer>(true);
        log.AppendLine("SkinnedMeshRenderers (" + skmR.Length + "):");
        foreach (var r in skmR)
            log.AppendLine("  " + r.gameObject.name + " active=" + r.gameObject.activeInHierarchy + " enabled=" + r.enabled + " mat=" + (r.sharedMaterial != null ? r.sharedMaterial.name : "null"));
        
        return log.ToString();
    }
}
