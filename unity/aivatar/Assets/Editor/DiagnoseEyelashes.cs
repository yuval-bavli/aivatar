using UnityEngine;
using UnityEditor;

/// DiagnoseEyelashes — find which renderers use the eyelash material and report their state
public static class DiagnoseEyelashes
{
    [MenuItem("Aivatar/Diagnose Eyelash Renderers")]
    public static string Run()
    {
        var lashMat = AssetDatabase.LoadAssetAtPath<Material>("Assets/Models/Avatar/Materials/MI_Face_EyelashesHiLODs.mat");
        if (lashMat == null) return "ERROR: material not found";

        var log = new System.Text.StringBuilder();
        log.AppendLine($"Eyelash mat texture: {lashMat.GetTexture("_BaseMap")?.name ?? "none"}");
        log.AppendLine($"Eyelash mat _Cutoff: {lashMat.GetFloat("_Cutoff")}");
        log.AppendLine();

        int found = 0;
        foreach (var r in GameObject.FindObjectsOfType<Renderer>(true))
        {
            foreach (var m in r.sharedMaterials)
            {
                if (m == lashMat)
                {
                    found++;
                    log.AppendLine($"  Renderer: {r.gameObject.name} (type={r.GetType().Name}, enabled={r.enabled}, active={r.gameObject.activeInHierarchy})");
                    log.AppendLine($"    Materials: {r.sharedMaterials.Length} slots");
                    for (int i = 0; i < r.sharedMaterials.Length; i++)
                        log.AppendLine($"      [{i}]: {r.sharedMaterials[i]?.name ?? "null"}");
                    break;
                }
            }
        }
        if (found == 0) log.AppendLine("No active renderers using eyelash material found!");
        return log.ToString();
    }
}
