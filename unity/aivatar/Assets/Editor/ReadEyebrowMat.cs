using UnityEngine;
using UnityEditor;

public static class ReadEyebrowMat
{
    public static string Run()
    {
        var mat = AssetDatabase.LoadAssetAtPath<Material>("Assets/Models/Avatar/Materials/Eyebrows.mat");
        if (mat == null) return "ERROR: Eyebrows.mat not found";

        var sb = new System.Text.StringBuilder();
        sb.AppendLine($"Shader: {mat.shader.name}");

        Color bc = mat.GetColor("_BaseColor");
        sb.AppendLine($"_BaseColor: R={bc.r:F3} G={bc.g:F3} B={bc.b:F3} A={bc.a:F3}");

        float cutoff = mat.GetFloat("_Cutoff");
        float alphaClip = mat.GetFloat("_AlphaClip");
        sb.AppendLine($"_Cutoff={cutoff:F3} _AlphaClip={alphaClip:F3}");

        bool alphaTest = mat.IsKeywordEnabled("_ALPHATEST_ON");
        sb.AppendLine($"_ALPHATEST_ON keyword: {alphaTest}");

        Texture baseMap = mat.GetTexture("_BaseMap");
        sb.AppendLine($"_BaseMap: {(baseMap != null ? baseMap.name : \"NULL\")}");
        sb.AppendLine($"RenderQueue: {mat.renderQueue}");

        // Now directly set to obvious test values and report
        mat.SetColor("_BaseColor", new Color(0.45f, 0.28f, 0.16f, 1f));
        mat.SetFloat("_Cutoff", 0.25f);
        mat.SetFloat("_AlphaClip", 1f);
        mat.EnableKeyword("_ALPHATEST_ON");

        // Load the white eyebrow texture explicitly
        var whiteTex = AssetDatabase.LoadAssetAtPath<Texture2D>("Assets/Models/Avatar/Textures/EyebrowCard_White.png");
        sb.AppendLine($"EyebrowCard_White.png loaded: {(whiteTex != null ? whiteTex.name : \"NOT FOUND\")}");
        if (whiteTex != null)
            mat.SetTexture("_BaseMap", whiteTex);

        EditorUtility.SetDirty(mat);
        AssetDatabase.SaveAssets();

        bc = mat.GetColor("_BaseColor");
        sb.AppendLine($">> Set BaseColor: R={bc.r:F3} G={bc.g:F3} B={bc.b:F3}");
        Texture newTex = mat.GetTexture("_BaseMap");
        sb.AppendLine($">> Set _BaseMap: {(newTex != null ? newTex.name : \"NULL\")}");
        return sb.ToString();
    }
}
