
using UnityEngine;
using UnityEditor;
public static class CheckBoundsAll
{
    [MenuItem("Aivatar/Check Bounds All")]
    public static string Run()
    {
        var log = new System.Text.StringBuilder();
        foreach (var mr in Object.FindObjectsOfType<MeshRenderer>(true))
        {
            var b = mr.bounds;
            log.AppendLine(mr.gameObject.name + ":");
            log.AppendLine("  center=" + b.center + " extents=" + b.extents);
            log.AppendLine("  Yrange=[" + (b.center.y - b.extents.y) + ", " + (b.center.y + b.extents.y) + "]");
            log.AppendLine("  scale=" + mr.transform.lossyScale);
        }
        return log.ToString();
    }
}
