using UnityEngine;
using UnityEditor;
using System.Text;

/// <summary>
/// Fine-tunes the eyebrow card mesh material to match reference:
/// - lighter warm brown color
/// - appropriate cutoff for natural hair strand density
/// </summary>
public static class TuneEyebrows
{
    // cutoff: higher = fewer/thinner strands; lower = denser/thicker
    // color: warm brown matching reference
    public static string Apply(float cutoff = 0.20f, float r = 0.42f, float g = 0.26f, float b = 0.15f)
    {
        var sb = new StringBuilder();

        Renderer browRenderer = null;
        foreach (var r2 in Resources.FindObjectsOfTypeAll<Renderer>())
        {
            if (r2.hideFlags != HideFlags.None) continue;
            if (r2.gameObject.name.ToLower().Contains("eyebrow") || r2.gameObject.name.ToLower().Contains("brow"))
            { browRenderer = r2; break; }
        }
        if (browRenderer == null) return "ERROR: no eyebrow renderer found";

        foreach (var m in browRenderer.sharedMaterials)
        {
            if (m == null) continue;
            m.SetFloat("_AlphaClip", 1f);
            m.EnableKeyword("_ALPHATEST_ON");
            m.SetFloat("_Cutoff", cutoff);
            m.SetColor("_BaseColor", new Color(r, g, b, 1f));
            m.renderQueue = 2450;

            // Reduce metallic/smoothness for natural matte look
            if (m.HasProperty("_Metallic")) m.SetFloat("_Metallic", 0f);
            if (m.HasProperty("_Smoothness")) m.SetFloat("_Smoothness", 0.2f);
            if (m.HasProperty("_SpecularHighlights")) m.SetFloat("_SpecularHighlights", 0f);

            EditorUtility.SetDirty(m);
        }
        AssetDatabase.SaveAssets();

        sb.AppendLine($"Eyebrow material tuned:");
        sb.AppendLine($"  Cutoff={cutoff} (higher=thinner strands)");
        sb.AppendLine($"  Color=({r:F2},{g:F2},{b:F2}) warm brown");
        return sb.ToString();
    }

    // Preset: light natural brown (closer to reference)
    public static string ApplyLight() => Apply(cutoff: 0.22f, r: 0.42f, g: 0.26f, b: 0.15f);

    // Preset: medium brown
    public static string ApplyMedium() => Apply(cutoff: 0.15f, r: 0.32f, g: 0.19f, b: 0.11f);

    // Preset: dark brow
    public static string ApplyDark() => Apply(cutoff: 0.10f, r: 0.22f, g: 0.13f, b: 0.08f);
}
