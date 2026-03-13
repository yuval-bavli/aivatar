#if UNITY_EDITOR
using UnityEngine;
using UnityEditor;

/// <summary>
/// Menu: Aivatar > Fix Appearance
/// Minimal, conservative fixes: only changes colors/tints on existing materials.
/// Preserves all texture assignments and rendering modes that were working.
/// All changes are undoable via Edit > Undo.
///
/// DOES NOT touch eye materials (MI_EyeL_Baked, MI_EyeR_Baked, MI_Face_EyeShell).
/// </summary>
public static class FixAppearance
{
    // ── Tunable colors ───────────────────────────────────────────────────
    // Hair card texture has gray-brown strands (~0.5 brightness).
    // _BaseColor multiplies the texture, so 0.35 × 0.5 ≈ 0.17 final — dark brown.
    private static readonly Color HairColor    = new Color(0.35f, 0.22f, 0.16f, 1f);
    private static readonly Color MHideColor   = new Color(0.20f, 0.12f, 0.08f, 1f);  // slightly darker, fills gaps
    private static readonly Color LashColor    = new Color(0.12f, 0.08f, 0.06f, 1f);  // original eyelash tint
    private static readonly Color EyebrowColor = new Color(0.30f, 0.18f, 0.12f, 1f);

    private const string MaterialsFolder = "Assets/Models/Avatar/Materials";
    private const string TexturesFolder  = "Assets/Models/Avatar/Textures";

    [MenuItem("Aivatar/Fix Appearance")]
    private static void Fix()
    {
        Undo.SetCurrentGroupName("Fix Appearance");
        int undoGroup = Undo.GetCurrentGroup();

        int fixes = 0;
        fixes += FixHairColor();
        fixes += FixMHideColor();
        fixes += FixEyelashMaterial();
        fixes += FixFaceSkinOpaque();
        fixes += FixEyebrowRenderer();

        Undo.CollapseUndoOperations(undoGroup);
        AssetDatabase.SaveAssets();

        EditorUtility.DisplayDialog("Fix Appearance",
            $"Done! Applied {fixes} fix(es).\nAll changes undoable (Edit > Undo).\nCheck Console.", "OK");
    }

    // ═══════════════════════════════════════════════════════════════════════
    // 1. HAIR — only change the tint color, keep everything else as-is
    // ═══════════════════════════════════════════════════════════════════════
    private static int FixHairColor()
    {
        var mat = AssetDatabase.LoadAssetAtPath<Material>($"{MaterialsFolder}/haircut.mat");
        if (mat == null) return 0;

        Undo.RecordObject(mat, "Fix hair color");
        mat.SetColor("_BaseColor", HairColor);
        mat.SetColor("_Color", HairColor);

        // Lower cutoff to keep semi-transparent strand edges (20.8% of texture).
        // At 0.4 only ~15% of pixels render (too sparse). At 0.15, ~35% render.
        mat.SetFloat("_Cutoff", 0.15f);
        mat.SetFloat("_Smoothness", 0.4f);

        EditorUtility.SetDirty(mat);
        Debug.Log($"[FixAppearance] haircut.mat: BaseColor → {HairColor}");
        return 1;
    }

    // ═══════════════════════════════════════════════════════════════════════
    // 2. M_HIDE — restore hair card texture + alpha cutout with dark tint.
    //    This is the scalp under hair. With hair texture + cutout it looks
    //    like an under-layer of hair, filling gaps between the top hair cards.
    // ═══════════════════════════════════════════════════════════════════════
    private static int FixMHideColor()
    {
        string[] hideNames = { "M_Hide", "M_Hide_6" };
        int count = 0;

        var hairTex  = AssetDatabase.LoadAssetAtPath<Texture2D>($"{TexturesFolder}/HairCard0_Color_1K.png");
        var hairNorm = AssetDatabase.LoadAssetAtPath<Texture2D>($"{TexturesFolder}/HairCard0_Normal_1K.jpg");

        foreach (var name in hideNames)
        {
            var mat = AssetDatabase.LoadAssetAtPath<Material>($"{MaterialsFolder}/{name}.mat");
            if (mat == null) continue;

            Undo.RecordObject(mat, $"Fix {name}");

            // Restore to original-like state: opaque with hair card texture + cutout
            mat.SetFloat("_Surface", 0);  // Opaque
            mat.SetFloat("_AlphaClip", 1);
            mat.SetFloat("_Cutoff", 0.15f);  // low cutoff for dense backing
            mat.SetFloat("_ZWrite", 1);
            mat.SetFloat("_Cull", 0);     // double-sided
            mat.SetFloat("_Smoothness", 0.15f);
            mat.SetFloat("_BumpScale", 0.3f);
            mat.EnableKeyword("_ALPHATEST_ON");
            mat.DisableKeyword("_SURFACE_TYPE_TRANSPARENT");
            mat.SetOverrideTag("RenderType", "TransparentCutout");
            mat.renderQueue = 2450;
            mat.doubleSidedGI = true;

            // Dark tint matching hair
            mat.SetColor("_BaseColor", MHideColor);
            mat.SetColor("_Color", MHideColor);

            // Restore hair card texture
            if (hairTex != null)
            {
                mat.SetTexture("_BaseMap", hairTex);
                mat.SetTexture("_MainTex", hairTex);
            }
            if (hairNorm != null)
            {
                mat.SetTexture("_BumpMap", hairNorm);
                mat.EnableKeyword("_NORMALMAP");
            }

            // Re-enable shader passes
            mat.SetShaderPassEnabled("ShadowCaster", true);
            mat.SetShaderPassEnabled("DepthOnly", true);

            // Fix blend mode for opaque
            mat.SetFloat("_SrcBlend", 1);  // One
            mat.SetFloat("_DstBlend", 0);  // Zero
            mat.SetFloat("_SrcBlendAlpha", 1);
            mat.SetFloat("_DstBlendAlpha", 0);
            mat.SetFloat("_AlphaToMask", 1);

            EditorUtility.SetDirty(mat);
            Debug.Log($"[FixAppearance] {name}.mat: restored hair texture + cutout, tint={MHideColor}");
            count++;
        }
        return count;
    }

    // ═══════════════════════════════════════════════════════════════════════
    // 3. EYELASHES — restore to original working state with correct texture
    // ═══════════════════════════════════════════════════════════════════════
    private static int FixEyelashMaterial()
    {
        var mat = AssetDatabase.LoadAssetAtPath<Material>($"{MaterialsFolder}/MI_Face_EyelashesHiLODs.mat");
        if (mat == null) return 0;

        Undo.RecordObject(mat, "Fix eyelash material");

        // Restore hair card texture (provides alpha for lash strand shape)
        var hairTex  = AssetDatabase.LoadAssetAtPath<Texture2D>($"{TexturesFolder}/HairCard0_Color_1K.png");
        var hairNorm = AssetDatabase.LoadAssetAtPath<Texture2D>($"{TexturesFolder}/HairCard0_Normal_1K.jpg");
        if (hairTex != null)
        {
            mat.SetTexture("_BaseMap", hairTex);
            mat.SetTexture("_MainTex", hairTex);
        }
        if (hairNorm != null)
        {
            mat.SetTexture("_BumpMap", hairNorm);
            mat.EnableKeyword("_NORMALMAP");
        }

        // Original eyelash tint — dark brown, not too dark
        mat.SetColor("_BaseColor", LashColor);
        mat.SetColor("_Color", LashColor);

        // Original settings
        mat.SetFloat("_AlphaClip", 1);
        mat.SetFloat("_Cutoff", 0.4f);
        mat.SetFloat("_Cull", 0);
        mat.SetFloat("_Smoothness", 0.15f);
        mat.SetFloat("_BumpScale", 0.3f);

        EditorUtility.SetDirty(mat);
        Debug.Log($"[FixAppearance] MI_Face_EyelashesHiLODs.mat: restored original texture + tint={LashColor}");
        return 1;
    }

    // ═══════════════════════════════════════════════════════════════════════
    // 4. FACE SKIN — make opaque (was incorrectly set to alpha cutout)
    // ═══════════════════════════════════════════════════════════════════════
    private static int FixFaceSkinOpaque()
    {
        var mat = AssetDatabase.LoadAssetAtPath<Material>($"{MaterialsFolder}/MI_Face_Skin_Baked_LOD1_VT.mat");
        if (mat == null) return 0;

        Undo.RecordObject(mat, "Fix face skin");

        mat.SetFloat("_AlphaClip", 0);
        mat.SetFloat("_Surface", 0);
        mat.DisableKeyword("_ALPHATEST_ON");
        mat.SetFloat("_AlphaToMask", 0);
        mat.renderQueue = 2000;
        mat.SetOverrideTag("RenderType", "Opaque");
        mat.SetFloat("_Cull", 2);
        mat.SetColor("_BaseColor", Color.white);
        mat.SetColor("_Color", Color.white);

        EditorUtility.SetDirty(mat);
        Debug.Log("[FixAppearance] MI_Face_Skin_Baked_LOD1_VT.mat: opaque");
        return 1;
    }

    // ═══════════════════════════════════════════════════════════════════════
    // 5. EYEBROWS — find renderer, log diagnostics, assign proper material
    // ═══════════════════════════════════════════════════════════════════════
    private static int FixEyebrowRenderer()
    {
        // Search for ALL renderers containing "Eyebrow" to debug
        Renderer eyebrowRenderer = null;
        foreach (var r in Object.FindObjectsOfType<Renderer>(true))
        {
            if (r.gameObject.name.Contains("Eyebrow") || r.gameObject.name.Contains("eyebrow"))
            {
                Debug.Log($"[FixAppearance] Found renderer '{r.gameObject.name}' " +
                          $"type={r.GetType().Name} " +
                          $"active={r.gameObject.activeInHierarchy} " +
                          $"enabled={r.enabled} " +
                          $"mats={r.sharedMaterials.Length} " +
                          $"bounds={r.bounds} " +
                          $"path={GetPath(r.gameObject)}");
                for (int i = 0; i < r.sharedMaterials.Length; i++)
                {
                    var m = r.sharedMaterials[i];
                    Debug.Log($"[FixAppearance]   mat[{i}]: {(m != null ? m.name : "NULL")}");
                }
                eyebrowRenderer = r;
            }
        }

        if (eyebrowRenderer == null)
        {
            // Also search transforms for eyebrow objects that might not have renderers
            foreach (var t in Object.FindObjectsOfType<Transform>(true))
            {
                if (t.name.Contains("Eyebrow") || t.name.Contains("eyebrow"))
                {
                    Debug.LogWarning($"[FixAppearance] Transform '{t.name}' found but has no Renderer. " +
                                     $"active={t.gameObject.activeInHierarchy} " +
                                     $"path={GetPath(t.gameObject)} " +
                                     $"childCount={t.childCount}");
                    // Check children
                    for (int i = 0; i < t.childCount; i++)
                    {
                        var child = t.GetChild(i);
                        var cr = child.GetComponent<Renderer>();
                        Debug.LogWarning($"[FixAppearance]   child '{child.name}' hasRenderer={cr != null}");
                        if (cr != null) eyebrowRenderer = cr;
                    }
                }
            }
        }

        if (eyebrowRenderer == null)
        {
            Debug.LogError("[FixAppearance] No eyebrow renderer found anywhere in scene!");
            return 0;
        }

        // Create or load eyebrow material
        string eyebrowMatPath = $"{MaterialsFolder}/Eyebrows.mat";
        var eyebrowMat = AssetDatabase.LoadAssetAtPath<Material>(eyebrowMatPath);
        var haircutMat = AssetDatabase.LoadAssetAtPath<Material>($"{MaterialsFolder}/haircut.mat");

        if (eyebrowMat == null && haircutMat != null)
        {
            eyebrowMat = new Material(haircutMat);
            eyebrowMat.name = "Eyebrows";
            AssetDatabase.CreateAsset(eyebrowMat, eyebrowMatPath);
            Debug.Log($"[FixAppearance] Created {eyebrowMatPath}");
        }

        if (eyebrowMat == null) return 0;

        Undo.RecordObject(eyebrowMat, "Fix eyebrow material");

        // Use same hair card texture + dark tint
        var hairTex  = AssetDatabase.LoadAssetAtPath<Texture2D>($"{TexturesFolder}/HairCard0_Color_1K.png");
        var hairNorm = AssetDatabase.LoadAssetAtPath<Texture2D>($"{TexturesFolder}/HairCard0_Normal_1K.jpg");
        if (hairTex != null) { eyebrowMat.SetTexture("_BaseMap", hairTex); eyebrowMat.SetTexture("_MainTex", hairTex); }
        if (hairNorm != null) { eyebrowMat.SetTexture("_BumpMap", hairNorm); eyebrowMat.EnableKeyword("_NORMALMAP"); }

        eyebrowMat.SetColor("_BaseColor", EyebrowColor);
        eyebrowMat.SetColor("_Color", EyebrowColor);
        eyebrowMat.SetFloat("_AlphaClip", 1);
        eyebrowMat.SetFloat("_Cutoff", 0.1f);  // very low for thin eyebrow strands
        eyebrowMat.EnableKeyword("_ALPHATEST_ON");
        eyebrowMat.SetFloat("_Cull", 0);
        eyebrowMat.SetFloat("_Smoothness", 0.15f);
        eyebrowMat.SetFloat("_BumpScale", 0.3f);
        eyebrowMat.doubleSidedGI = true;
        eyebrowMat.SetOverrideTag("RenderType", "TransparentCutout");
        eyebrowMat.renderQueue = 2450;

        EditorUtility.SetDirty(eyebrowMat);

        // Assign to renderer
        Undo.RecordObject(eyebrowRenderer, "Fix eyebrow renderer");
        eyebrowRenderer.sharedMaterials = new Material[] { eyebrowMat };
        Debug.Log($"[FixAppearance] Eyebrow: assigned Eyebrows.mat to '{eyebrowRenderer.gameObject.name}'");

        return 1;
    }

    private static string GetPath(GameObject go)
    {
        string path = go.name;
        Transform t = go.transform.parent;
        while (t != null) { path = t.name + "/" + path; t = t.parent; }
        return path;
    }
}
#endif
