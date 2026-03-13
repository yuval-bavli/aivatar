using UnityEngine;
using UnityEditor;
using System.Collections.Generic;

/// <summary>
/// Tools → Assign MetaHuman Textures
/// Assigns the correct textures to each MetaHuman material and fixes
/// M_Hide materials so hidden geometry (scalp under hair) becomes invisible.
/// Materials: Assets/Models/Avatar/Materials/
/// Textures:  Assets/Models/Avatar/Textures/
/// </summary>
public static class AssignMetaHumanMaterials
{
    private const string MatPath = "Assets/Models/Avatar/Materials";
    private const string TexPath = "Assets/Models/Avatar/Textures";

    // (materialName, baseMapTexture, normalMapTexture)
    // normalMapTexture = null → skip normal map slot
    private static readonly (string mat, string baseMap, string normalMap)[] Assignments =
    {
        ("MI_Body_Baked_VT",           "T_Body_BC_VT",       "T_Body_N_VT"),
        ("MI_Body_Baked_VT 1",         "T_Body_BC_VT",       "T_Body_N_VT"),
        ("MI_EyeL_Baked",              "T_EyeIrisL_BC",      "T_EyeIrisL_N"),
        ("MI_EyeR_Baked",              "T_EyeIrisR_BC",       "T_EyeIrisR_N"),
        // Face skin — T_Face_Basecolor_Animated_CM1 is the actual diffuse albedo
        ("MI_Face_Skin_Baked_LOD1_VT", "T_Face_Basecolor_Animated_CM1", "T_Face_Normal_Animated_WM1"),
        ("MI_Teeth_Baked",             "T_Teeth_BC",          "T_Teeth_N"),
        ("haircut",                    "HairCard0_Color_1K",  null),
    };

    // These Unreal "hide" materials make geometry invisible under hair.
    // In Unity they must be fully transparent or the scalp bleeds through.
    private static readonly string[] HideMaterials = { "M_Hide", "M_Hide_6" };

    [MenuItem("Tools/Assign MetaHuman Textures")]
    private static void Assign()
    {
        int assigned = 0;
        int skipped  = 0;

        // ── Texture assignments ──────────────────────────────────────────────
        foreach (var (matName, baseMapName, normalMapName) in Assignments)
        {
            var mat = LoadAsset<Material>(MatPath, matName);
            if (mat == null)
            {
                Debug.LogWarning($"[MetaHuman] Material not found: '{matName}'");
                skipped++;
                continue;
            }

            var baseMap = LoadAsset<Texture2D>(TexPath, baseMapName);
            if (baseMap != null)
            {
                mat.SetTexture("_BaseMap", baseMap);
                Debug.Log($"[MetaHuman] {matName} → _BaseMap = {baseMapName}");
            }
            else
            {
                Debug.LogWarning($"[MetaHuman] Texture not found: '{baseMapName}' (for {matName})");
            }

            if (normalMapName != null)
            {
                var normalMap = LoadAsset<Texture2D>(TexPath, normalMapName);
                if (normalMap != null)
                {
                    EnsureNormalMap(normalMap);
                    mat.SetTexture("_BumpMap", normalMap);
                    mat.EnableKeyword("_NORMALMAP");
                    Debug.Log($"[MetaHuman] {matName} → _BumpMap = {normalMapName}");
                }
                else
                {
                    Debug.LogWarning($"[MetaHuman] Texture not found: '{normalMapName}' (for {matName})");
                }
            }

            // _BaseColor multiplies the texture — black kills it, must be white
            mat.SetColor("_BaseColor", Color.white);
            mat.SetColor("_Color",     Color.white);

            EditorUtility.SetDirty(mat);
            assigned++;
        }

        // ── Make M_Hide materials fully transparent ──────────────────────────
        foreach (var hideName in HideMaterials)
        {
            var mat = LoadAsset<Material>(MatPath, hideName);
            if (mat == null)
            {
                Debug.LogWarning($"[MetaHuman] Hide material not found: '{hideName}'");
                continue;
            }

            MakeTransparent(mat);
            EditorUtility.SetDirty(mat);
            Debug.Log($"[MetaHuman] '{hideName}' → set to fully transparent");
        }

        AssetDatabase.SaveAssets();
        Debug.Log($"[MetaHuman] Done — {assigned} material(s) updated, {skipped} skipped.");
        EditorUtility.DisplayDialog("Assign MetaHuman Textures",
            $"Done!\n{assigned} material(s) updated\n{skipped} skipped (check Console)", "OK");
    }

    /// <summary>
    /// Switches a URP/Lit material to Transparent surface with alpha = 0.
    /// </summary>
    private static void MakeTransparent(Material mat)
    {
        // URP surface type: 0 = Opaque, 1 = Transparent
        mat.SetFloat("_Surface", 1);
        mat.SetFloat("_Blend",   0);   // Alpha blend
        mat.SetFloat("_ZWrite",  0);

        mat.SetColor("_BaseColor", new Color(0, 0, 0, 0));
        mat.SetColor("_Color",     new Color(0, 0, 0, 0));

        mat.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
        mat.DisableKeyword("_ALPHAPREMULTIPLY_ON");

        mat.renderQueue = (int)UnityEngine.Rendering.RenderQueue.Transparent;

        // Tell Unity the material properties changed
        mat.SetShaderPassEnabled("ShadowCaster", false);
    }

    private static T LoadAsset<T>(string folder, string name) where T : UnityEngine.Object
    {
        var guids = AssetDatabase.FindAssets($"{name} t:{typeof(T).Name}", new[] { folder });
        foreach (var guid in guids)
        {
            var path  = AssetDatabase.GUIDToAssetPath(guid);
            var asset = AssetDatabase.LoadAssetAtPath<T>(path);
            if (asset != null && asset.name == name)
                return asset;
        }
        return null;
    }

    private static void EnsureNormalMap(Texture2D tex)
    {
        var path     = AssetDatabase.GetAssetPath(tex);
        var importer = AssetImporter.GetAtPath(path) as TextureImporter;
        if (importer != null && importer.textureType != TextureImporterType.NormalMap)
        {
            importer.textureType = TextureImporterType.NormalMap;
            importer.SaveAndReimport();
        }
    }
}
