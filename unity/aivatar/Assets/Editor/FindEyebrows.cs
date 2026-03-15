
using UnityEngine;
using UnityEditor;

public static class FindEyebrows
{
    [MenuItem("Aivatar/Find Eyebrows")]
    public static string Run()
    {
        var log = new System.Text.StringBuilder();
        var all = Object.FindObjectsOfType<SkinnedMeshRenderer>(true);
        log.AppendLine("All SkinnedMeshRenderers (" + all.Length + " total):");
        foreach (var smr in all)
        {
            log.AppendLine(smr.gameObject.name + " | active=" + smr.gameObject.activeInHierarchy + " | enabled=" + smr.enabled);
        }
        return log.ToString();
    }
}
