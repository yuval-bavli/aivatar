
using UnityEngine;
using UnityEditor;
using UnityEngine.Rendering;
public static class ReEnableEyebrows2
{
    [MenuItem("Aivatar/ReEnable Eyebrows 2")]
    public static string Run()
    {
        foreach (var mr in Object.FindObjectsOfType<MeshRenderer>(true))
            if (mr.gameObject.name.ToLower().Contains("brow"))
            {
                mr.enabled = true;
                var mat = mr.sharedMaterial;
                if (mat != null) { mat.SetFloat("_Cutoff", 0.4f); EditorUtility.SetDirty(mat); }
                AssetDatabase.SaveAssets();
                return "Re-enabled with Cutoff=0.4: " + mr.gameObject.name;
            }
        return "Not found";
    }
}
