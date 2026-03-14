using UnityEngine;
using UnityEditor;

public static class FixAppearanceV3
{
    [MenuItem("Aivatar/Fix Appearance V3")]
    public static string Run()
    {
        var log = new System.Text.StringBuilder();

        // ============================================================
        // 1. HAIR: Darker, denser coverage, softer edges
        // ============================================================
        var hairMat = AssetDatabase.LoadAssetAtPath<Material>(
            "Assets/Models/Avatar/Materials/haircut.mat");
        if (hairMat != null)
        {
            // Darker brown - closer to the original MetaHuman
            hairMat.SetColor("_BaseColor", new Color(0.20f, 0.13f, 0.09f, 1f));
            // Lower cutoff = more hair strands visible = denser hair
            hairMat.SetFloat("_Cutoff", 0.08f);
            hairMat.SetFloat("_Smoothness", 0.50f);
            // Keep alpha test for now
            hairMat.SetFloat("_AlphaClip", 1f);
            hairMat.EnableKeyword("_ALPHATEST_ON");
            // Double-sided rendering
            hairMat.SetFloat("_Cull", 0f);
            EditorUtility.SetDirty(hairMat);
            log.AppendLine("FIXED: Hair darkened, cutoff lowered for density");
        }

        // ============================================================
        // 2. M_HIDE: Render as dark scalp backing (visible under hair)
        //    Instead of transparent, use dark opaque scalp color
        //    This hides the skin texture's lighter scalp area
        // ============================================================
        foreach (var hideName in new[] {
            "Assets/Models/Avatar/Materials/M_Hide.mat",
            "Assets/Models/Avatar/Materials/M_Hide_6.mat" })
        {
            var hideMat = AssetDatabase.LoadAssetAtPath<Material>(hideName);
            if (hideMat != null)
            {
                // Make it opaque dark - acts as dark scalp under hair
                hideMat.SetFloat("_Surface", 0f); // Opaque
                hideMat.DisableKeyword("_SURFACE_TYPE_TRANSPARENT");
                hideMat.DisableKeyword("_ALPHAPREMULTIPLY_ON");
                hideMat.DisableKeyword("_ALPHATEST_ON");
                hideMat.SetFloat("_AlphaClip", 0f);
                hideMat.SetColor("_BaseColor", new Color(0.10f, 0.07f, 0.05f, 1f)); // Very dark brown
                hideMat.SetFloat("_Smoothness", 0.1f);
                hideMat.SetTexture("_BaseMap", null); // No texture, just flat dark color
                hideMat.SetTexture("_BumpMap", null);
                hideMat.SetFloat("_Cull", 2f); // Back face culling
                hideMat.SetFloat("_ZWrite", 1f);
                hideMat.SetFloat("_SrcBlend", (float)UnityEngine.Rendering.BlendMode.One);
                hideMat.SetFloat("_DstBlend", (float)UnityEngine.Rendering.BlendMode.Zero);
                hideMat.renderQueue = 2000;
                EditorUtility.SetDirty(hideMat);
                log.AppendLine($"FIXED: {hideName} set to dark opaque scalp");
            }
        }

        // ============================================================
        // 3. EYEBROWS: Make more visible
        // ============================================================
        var browMat = AssetDatabase.LoadAssetAtPath<Material>(
            "Assets/Models/Avatar/Materials/Eyebrows.mat");
        if (browMat != null)
        {
            // Darker and more visible
            browMat.SetColor("_BaseColor", new Color(0.18f, 0.12f, 0.08f, 1f));
            browMat.SetFloat("_Cutoff", 0.05f); // Very low to show all brow strands
            browMat.SetFloat("_Smoothness", 0.15f);
            browMat.SetFloat("_AlphaClip", 1f);
            browMat.EnableKeyword("_ALPHATEST_ON");
            browMat.SetFloat("_Cull", 0f); // Double-sided
            browMat.renderQueue = 2451;
            EditorUtility.SetDirty(browMat);
            log.AppendLine("FIXED: Eyebrows darkened, cutoff minimized");
        }

        // ============================================================
        // 4. EYELASHES: Fine-tune
        // ============================================================
        var lashMat = AssetDatabase.LoadAssetAtPath<Material>(
            "Assets/Models/Avatar/Materials/MI_Face_EyelashesHiLODs.mat");
        if (lashMat != null)
        {
            // Medium brown - visible but not overpowering
            lashMat.SetColor("_BaseColor", new Color(0.18f, 0.12f, 0.08f, 1f));
            lashMat.SetFloat("_Cutoff", 0.5f);
            EditorUtility.SetDirty(lashMat);
            log.AppendLine("FIXED: Eyelashes fine-tuned");
        }

        AssetDatabase.SaveAssets();

        string result = log.ToString();
        Debug.Log(result);
        return result;
    }
}
