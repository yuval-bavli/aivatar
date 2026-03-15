
using UnityEngine;
using UnityEditor;
using UnityEngine.Rendering;

public static class ReEnableEyebrows
{
    [MenuItem("Aivatar/ReEnable Eyebrows")]
    public static string Run()
    {
        var log = new System.Text.StringBuilder();
        var allMeshR = Object.FindObjectsOfType<MeshRenderer>(true);
        foreach (var mr in allMeshR)
        {
            if (mr.gameObject.name.ToLower().Contains("brow"))
            {
                mr.enabled = true;
                log.AppendLine("Re-enabled: " + mr.gameObject.name);
                var mat = mr.sharedMaterial;
                if (mat != null)
                {
                    // Higher cutoff to prevent card bleed  
                    mat.SetFloat("_Cutoff", 0.35f);
                    EditorUtility.SetDirty(mat);
                    log.AppendLine("Set _Cutoff=0.35 on: " + mat.name);
                }
            }
        }
        AssetDatabase.SaveAssets();
        return log.ToString();
    }
}
