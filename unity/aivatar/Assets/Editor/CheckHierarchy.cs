
using UnityEngine;
using UnityEditor;

public static class CheckHierarchy
{
    [MenuItem("Aivatar/Check Hierarchy")]
    public static string Run()
    {
        var log = new System.Text.StringBuilder();
        var allMeshR = Object.FindObjectsOfType<MeshRenderer>(true);
        foreach (var mr in allMeshR)
        {
            log.AppendLine(mr.gameObject.name + ":");
            log.AppendLine("  localPos=" + mr.transform.localPosition + " worldPos=" + mr.transform.position);
            log.AppendLine("  localScale=" + mr.transform.localScale);
            var parent = mr.transform.parent;
            if (parent != null) log.AppendLine("  parent=" + parent.name + " parentPos=" + parent.position);
        }
        return log.ToString();
    }
}
