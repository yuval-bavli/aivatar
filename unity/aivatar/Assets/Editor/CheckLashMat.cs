using UnityEngine;
using UnityEditor;

public static class CheckLashMat
{
    public static string Check()
    {
        var mat = AssetDatabase.LoadAssetAtPath<Material>("Assets/Models/Avatar/Materials/MI_Face_EyelashesHiLODs.mat");
        if (mat == null) return "ERROR: mat not found";
        float cutoff = mat.GetFloat("_Cutoff");
        float alphaClip = mat.GetFloat("_AlphaClip");
        Color baseColor = mat.GetColor("_BaseColor");
        bool hasAlphaTest = mat.IsKeywordEnabled("_ALPHATEST_ON");
        return $"Cutoff={cutoff} | AlphaClip={alphaClip} | BaseColor.a={baseColor.a} | ALPHATEST_ON={hasAlphaTest}";
    }

    public static string HideEyelashes()
    {
        // Completely hide eyelashes: set cutoff to max so all pixels are discarded
        string[] matPaths = {
            "Assets/Models/Avatar/Materials/MI_Face_EyelashesHiLODs.mat",
            "Assets/Models/Avatar/Materials/AvatarEyelashes.mat",
        };
        var sb = new System.Text.StringBuilder();
        foreach (var p in matPaths)
        {
            var mat = AssetDatabase.LoadAssetAtPath<Material>(p);
            if (mat == null) { sb.AppendLine($"NOT FOUND: {p}"); continue; }
            mat.SetFloat("_Cutoff", 1.0f);
            mat.SetFloat("_AlphaClip", 1.0f);
            mat.EnableKeyword("_ALPHATEST_ON");
            // Also set alpha to 0 as backup
            Color c = mat.GetColor("_BaseColor");
            c.a = 0.0f;
            mat.SetColor("_BaseColor", c);
            EditorUtility.SetDirty(mat);
            sb.AppendLine($"Hidden: {System.IO.Path.GetFileName(p)} (cutoff=1.0, alpha=0)");
        }
        AssetDatabase.SaveAssets();
        return sb.ToString();
    }
}
