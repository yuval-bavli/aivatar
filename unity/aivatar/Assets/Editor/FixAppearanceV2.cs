using UnityEngine;
using UnityEditor;

public static class FixAppearanceV2
{
    [MenuItem("Aivatar/Fix Appearance V2")]
    public static string Run()
    {
        var log = new System.Text.StringBuilder();

        // ============================================================
        // 1. FIX HAIR: Assign haircut material to the hair mesh
        // ============================================================
        var hairGO = FindByName("Hair_M_BobMessy_CardsMesh_Group0_LOD0");
        if (hairGO != null)
        {
            var hairRenderer = hairGO.GetComponent<MeshRenderer>();
            if (hairRenderer != null)
            {
                var haircutMat = AssetDatabase.LoadAssetAtPath<Material>(
                    "Assets/Models/Avatar/Materials/haircut.mat");

                if (haircutMat != null)
                {
                    // Hair mesh has 1 submesh - assign just the haircut material
                    hairRenderer.sharedMaterials = new Material[] { haircutMat };
                    EditorUtility.SetDirty(hairRenderer);
                    log.AppendLine("FIXED: Hair mesh assigned haircut material");
                }
                else
                    log.AppendLine("ERROR: Could not find haircut.mat");
            }
        }
        else
            log.AppendLine("WARNING: Could not find hair mesh");

        // ============================================================
        // 2. FIX HAIRCUT MATERIAL: Tune for better appearance
        // ============================================================
        var hairMat = AssetDatabase.LoadAssetAtPath<Material>(
            "Assets/Models/Avatar/Materials/haircut.mat");
        if (hairMat != null)
        {
            // Dark brown base color matching the original MetaHuman
            hairMat.SetColor("_BaseColor", new Color(0.28f, 0.18f, 0.13f, 1f));
            // Alpha cutoff - balance between coverage and clean edges
            hairMat.SetFloat("_Cutoff", 0.12f);
            // Hair should have some sheen
            hairMat.SetFloat("_Smoothness", 0.45f);
            EditorUtility.SetDirty(hairMat);
            log.AppendLine("FIXED: Haircut material tuned");
        }

        // ============================================================
        // 3. FIX M_HIDE MATERIALS: These are scalp/hidden geometry
        //    They should be fully transparent or use very dark color
        // ============================================================
        foreach (var hideName in new[] {
            "Assets/Models/Avatar/Materials/M_Hide.mat",
            "Assets/Models/Avatar/Materials/M_Hide_6.mat" })
        {
            var hideMat = AssetDatabase.LoadAssetAtPath<Material>(hideName);
            if (hideMat != null)
            {
                // Make these transparent so scalp doesn't show through hair gaps
                hideMat.SetFloat("_Surface", 1f); // Transparent
                hideMat.SetFloat("_Blend", 0f); // Alpha blend
                hideMat.SetColor("_BaseColor", new Color(0.15f, 0.10f, 0.07f, 0f)); // Fully transparent
                hideMat.SetFloat("_AlphaClip", 0f);
                hideMat.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
                hideMat.EnableKeyword("_ALPHAPREMULTIPLY_ON");
                hideMat.DisableKeyword("_ALPHATEST_ON");
                hideMat.renderQueue = 3000;
                // Set proper blend modes for transparency
                hideMat.SetFloat("_SrcBlend", (float)UnityEngine.Rendering.BlendMode.One);
                hideMat.SetFloat("_DstBlend", (float)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
                hideMat.SetFloat("_ZWrite", 0f);
                EditorUtility.SetDirty(hideMat);
                log.AppendLine($"FIXED: {hideName} made fully transparent");
            }
        }

        // ============================================================
        // 4. FIX EYELASHES: Less bold, more natural
        // ============================================================
        var lashMat = AssetDatabase.LoadAssetAtPath<Material>(
            "Assets/Models/Avatar/Materials/MI_Face_EyelashesHiLODs.mat");
        if (lashMat != null)
        {
            // Lighter tint - dark brown instead of near-black
            lashMat.SetColor("_BaseColor", new Color(0.22f, 0.16f, 0.12f, 1f));
            // Higher cutoff means thinner/sparser lashes
            lashMat.SetFloat("_Cutoff", 0.55f);
            lashMat.SetFloat("_Smoothness", 0.3f);
            EditorUtility.SetDirty(lashMat);
            log.AppendLine("FIXED: Eyelash material lightened and thinned");
        }

        // ============================================================
        // 5. FIX EYEBROWS: Ensure visible with proper settings
        // ============================================================
        var browMat = AssetDatabase.LoadAssetAtPath<Material>(
            "Assets/Models/Avatar/Materials/Eyebrows.mat");
        if (browMat != null)
        {
            // Slightly lighter brown for natural eyebrows
            browMat.SetColor("_BaseColor", new Color(0.25f, 0.16f, 0.11f, 1f));
            browMat.SetFloat("_Cutoff", 0.08f); // Very low to show thin brow strands
            browMat.SetFloat("_Smoothness", 0.2f);
            // Ensure alpha clip is on
            browMat.SetFloat("_AlphaClip", 1f);
            browMat.EnableKeyword("_ALPHATEST_ON");
            // Double-sided
            browMat.SetFloat("_Cull", 0f);
            browMat.renderQueue = 2451; // Render just after opaque, before transparent
            // Make sure it renders on top of face skin
            browMat.SetFloat("_ZWrite", 1f);
            EditorUtility.SetDirty(browMat);
            log.AppendLine("FIXED: Eyebrow material adjusted");
        }

        // Check eyebrow renderer
        var browGO = FindByName("Eyebrows_M_Natural_CardsMesh_Group0_LOD0");
        if (browGO != null)
        {
            var browRenderer = browGO.GetComponent<MeshRenderer>();
            if (browRenderer != null)
            {
                if (browMat != null)
                {
                    browRenderer.sharedMaterials = new Material[] { browMat };
                    EditorUtility.SetDirty(browRenderer);
                }
                log.AppendLine($"Eyebrows: renderer enabled={browRenderer.enabled}, GO active={browGO.activeInHierarchy}");
            }
        }

        // ============================================================
        // 6. FIX OUTFIT: White T-shirt like original MetaHuman
        // ============================================================
        var outfitsGO = FindByName("model4_Outfits");
        if (outfitsGO != null)
        {
            var outfitRenderer = outfitsGO.GetComponent<SkinnedMeshRenderer>();
            if (outfitRenderer != null)
            {
                var mats = outfitRenderer.sharedMaterials;
                for (int i = 0; i < mats.Length; i++)
                {
                    if (mats[i] != null)
                    {
                        // White/light gray for T-shirt
                        mats[i].SetColor("_BaseColor", new Color(0.85f, 0.85f, 0.85f, 1f));
                        mats[i].SetFloat("_Smoothness", 0.2f);
                        EditorUtility.SetDirty(mats[i]);
                        log.AppendLine($"FIXED: Outfit mat[{i}] ({mats[i].name}) set to light gray");
                    }
                }
            }
        }

        // ============================================================
        // 7. FIX EYE SHELL: Should be clear with no hair texture
        // ============================================================
        var eyeShellMat = AssetDatabase.LoadAssetAtPath<Material>(
            "Assets/Models/Avatar/Materials/MI_Face_EyeShell.mat");
        if (eyeShellMat != null)
        {
            // Clear the base map - eye shell should be transparent cornea overlay
            eyeShellMat.SetTexture("_BaseMap", null);
            eyeShellMat.SetTexture("_BumpMap", null);
            eyeShellMat.SetColor("_BaseColor", new Color(1f, 1f, 1f, 0.02f));
            eyeShellMat.SetFloat("_Smoothness", 0.98f);
            EditorUtility.SetDirty(eyeShellMat);
            log.AppendLine("FIXED: Eye shell cleared of hair texture");
        }

        // ============================================================
        // 8. FIX LACRIMAL FLUID: Should not use hair texture
        // ============================================================
        var lacrimalMat = AssetDatabase.LoadAssetAtPath<Material>(
            "Assets/Models/Avatar/Materials/MI_Face_LacrimalFluid.mat");
        if (lacrimalMat != null)
        {
            lacrimalMat.SetTexture("_BumpMap", null); // Remove hair normal from lacrimal
            lacrimalMat.SetColor("_BaseColor", new Color(1f, 1f, 1f, 0.3f));
            lacrimalMat.SetFloat("_Smoothness", 0.95f);
            lacrimalMat.SetFloat("_Surface", 1f); // Transparent
            lacrimalMat.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
            lacrimalMat.SetFloat("_SrcBlend", (float)UnityEngine.Rendering.BlendMode.One);
            lacrimalMat.SetFloat("_DstBlend", (float)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
            lacrimalMat.SetFloat("_ZWrite", 0f);
            lacrimalMat.renderQueue = 3000;
            EditorUtility.SetDirty(lacrimalMat);
            log.AppendLine("FIXED: Lacrimal fluid material cleaned up");
        }

        AssetDatabase.SaveAssets();

        string result = log.ToString();
        Debug.Log(result);
        return result;
    }

    static GameObject FindByName(string name)
    {
        foreach (var go in Object.FindObjectsOfType<GameObject>())
        {
            if (go.name == name) return go;
        }
        return null;
    }
}
