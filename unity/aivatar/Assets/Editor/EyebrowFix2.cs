using UnityEngine;
using UnityEditor;

public static class EyebrowFix2
{
    public static string SetColor()
    {
        var mat = AssetDatabase.LoadAssetAtPath<Material>("Assets/Models/Avatar/Materials/Eyebrows.mat");
        if (mat == null) return "ERROR: mat not found";

        // Load white eyebrow texture
        var tex = AssetDatabase.LoadAssetAtPath<Texture2D>("Assets/Models/Avatar/Textures/EyebrowCard_White.png");
        string texStatus = tex != null ? tex.name : "NOT FOUND - using null";
        if (tex != null) mat.SetTexture("_BaseMap", tex);

        mat.SetColor("_BaseColor", new Color(0.45f, 0.28f, 0.16f, 1f));
        mat.SetFloat("_Cutoff", 0.25f);
        mat.SetFloat("_AlphaClip", 1f);
        mat.EnableKeyword("_ALPHATEST_ON");
        mat.renderQueue = 2450;

        EditorUtility.SetDirty(mat);
        AssetDatabase.SaveAssets();

        Color bc = mat.GetColor("_BaseColor");
        return "Done. BaseColor=" + bc.r.ToString("F2") + "," + bc.g.ToString("F2") + "," + bc.b.ToString("F2") + " Tex=" + texStatus;
    }
}
