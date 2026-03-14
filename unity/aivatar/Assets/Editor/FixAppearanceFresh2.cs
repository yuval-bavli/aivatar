using UnityEngine;
using UnityEditor;

public static class FixAppearanceFresh2
{
    [MenuItem("Aivatar/Fix Appearance Fresh2")]
    public static string Run()
    {
        var log = new System.Text.StringBuilder();

        // ============================================================
        // 1. HAIR: Back to alpha cutout but with better tuning
        // ============================================================
        var hairMat = AssetDatabase.LoadAssetAtPath<Material>(
            "Assets/Models/Avatar/Materials/haircut.mat");
        if (hairMat != null)
        {
            // Back to opaque + alpha cutout
            hairMat.SetFloat("_Surface", 0f); // Opaque
            hairMat.DisableKeyword("_SURFACE_TYPE_TRANSPARENT");
            hairMat.DisableKeyword("_ALPHAPREMULTIPLY_ON");
            hairMat.SetFloat("_AlphaClip", 1f);
            hairMat.EnableKeyword("_ALPHATEST_ON");
            hairMat.SetFloat("_SrcBlend", (float)UnityEngine.Rendering.BlendMode.One);
            hairMat.SetFloat("_DstBlend", (float)UnityEngine.Rendering.BlendMode.Zero);
            hairMat.SetFloat("_ZWrite", 1f);
            hairMat.renderQueue = 2450;

            // Moderate cutoff - not too low (blocky) or too high (sparse)
            hairMat.SetFloat("_Cutoff", 0.15f);
            // Warm medium-dark brown
            hairMat.SetColor("_BaseColor", new Color(0.22f, 0.15f, 0.10f, 1f));
            // Low smoothness to reduce shiny flat-plane look
            hairMat.SetFloat("_Smoothness", 0.20f);
            hairMat.SetFloat("_Metallic", 0f);
            hairMat.SetFloat("_Cull", 0f); // Double-sided
            // Disable env reflections (avoids blue skybox tint on hair)
            hairMat.DisableKeyword("_SPECULARHIGHLIGHTS_ON");
            hairMat.DisableKeyword("_ENVIRONMENTREFLECTIONS_ON");
            EditorUtility.SetDirty(hairMat);
            log.AppendLine("Hair: alpha cutout, cutoff=0.15, warm brown, low smoothness");
        }

        // ============================================================
        // 2. EYELASHES: Even lighter, thinner
        // ============================================================
        var lashMat = AssetDatabase.LoadAssetAtPath<Material>(
            "Assets/Models/Avatar/Materials/MI_Face_EyelashesHiLODs.mat");
        if (lashMat != null)
        {
            // Try the opacity mask as the base map for better alpha shape
            var lashOpacityMask = AssetDatabase.LoadAssetAtPath<Texture2D>(
                "Assets/Models/Avatar/MI_Face_EyelashesHiLODs_OpacityMask_8.png");
            var hairTex = AssetDatabase.LoadAssetAtPath<Texture2D>(
                "Assets/Models/Avatar/Textures/HairCard0_Color_1K.png");

            // Use hair card texture (has proper alpha channel for hair strands)
            lashMat.SetTexture("_BaseMap", hairTex);
            // Very light brown - almost skin-colored
            lashMat.SetColor("_BaseColor", new Color(0.35f, 0.25f, 0.20f, 1f));
            // Very high cutoff for thin, wispy lashes
            lashMat.SetFloat("_Cutoff", 0.7f);
            lashMat.SetFloat("_AlphaClip", 1f);
            lashMat.EnableKeyword("_ALPHATEST_ON");
            lashMat.SetFloat("_Smoothness", 0.1f);
            lashMat.SetFloat("_Cull", 0f);
            lashMat.SetFloat("_Surface", 0f);
            lashMat.renderQueue = 2450;
            lashMat.DisableKeyword("_SPECULARHIGHLIGHTS_ON");
            lashMat.DisableKeyword("_ENVIRONMENTREFLECTIONS_ON");
            EditorUtility.SetDirty(lashMat);
            log.AppendLine("Eyelashes: very light, very high cutoff (0.7)");
        }

        // ============================================================
        // 3. Eyebrows: Keep disabled for now
        // ============================================================

        AssetDatabase.SaveAssets();
        string result = log.ToString();
        Debug.Log(result);
        return result;
    }
}
