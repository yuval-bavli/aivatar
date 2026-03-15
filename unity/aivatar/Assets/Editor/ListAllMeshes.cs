
using UnityEngine;
using UnityEditor;

public static class ListAllMeshes
{
    [MenuItem("Aivatar/List All Meshes")]
    public static string Run()
    {
        var log = new System.Text.StringBuilder();
        foreach (var mr in Object.FindObjectsOfType<MeshRenderer>(true))
        {
            log.AppendLine(mr.gameObject.name + " | enabled=" + mr.enabled + " | mat=" + (mr.sharedMaterial != null ? mr.sharedMaterial.name : "null") + " | bounds.center=" + mr.bounds.center);
        }
        return log.ToString();
    }
}
