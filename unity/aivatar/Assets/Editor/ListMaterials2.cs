
using UnityEngine;
using UnityEditor;

public static class ListMaterials2
{
    [MenuItem("Aivatar/List Materials 2")]
    public static string Run()
    {
        var log = new System.Text.StringBuilder();
        foreach (var mr in Object.FindObjectsOfType<MeshRenderer>(true))
        {
            log.AppendLine("--- " + mr.gameObject.name + " ---");
            var mats = mr.sharedMaterials;
            for (int i = 0; i < mats.Length; i++)
                log.AppendLine("  [" + i + "] " + (mats[i] != null ? mats[i].name : "null"));
        }
        foreach (var smr in Object.FindObjectsOfType<SkinnedMeshRenderer>(true))
        {
            log.AppendLine("--- " + smr.gameObject.name + " (Skinned) ---");
            var mats = smr.sharedMaterials;
            for (int i = 0; i < mats.Length; i++)
                log.AppendLine("  [" + i + "] " + (mats[i] != null ? mats[i].name : "null"));
        }
        return log.ToString();
    }
}
