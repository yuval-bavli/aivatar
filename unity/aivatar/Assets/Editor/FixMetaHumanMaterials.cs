using UnityEngine;
using UnityEditor;
using System.Linq;
using System.Collections.Generic;

/// <summary>
/// Menu: Aivatar > Fix MetaHuman Materials
/// Extracts FBX-embedded materials, resets broken shaders, and assigns
/// the correct MetaHuman textures to each material by name.
/// </summary>
public static class FixMetaHumanMaterials
{
    private const string TexturesFolder  = "Assets/Models/Avatar/Textures";
    private const string MaterialsFolder = "Assets/Models/Avatar/Materials";

    // ── Exact texture-name → material assignment table ─────────────────────
    // Key   = lowercase substring to match against the material name
    // Value = (albedoTextureName, normalTextureName)  — null = skip that slot
    private static readonly (string matKey, string albedo, string normal)[] Assignments =
    {
        // Body skin
        ("avatarbody",      "T_Body_BC_VT",           "T_Body_N_VT"),
        // Head / face
        ("head",            "T_Head_BC_VT",            "T_Head_N_VT"),
        ("face",            "T_Head_BC_VT",            "T_Head_N_VT"),
        // Eyes — left  (sclera as main, iris logged separately)
        ("lefteyeball",     "T_EyeScleraL_BC",         "T_EyeScleraL_N"),
        ("eyeleft",         "T_EyeScleraL_BC",         "T_EyeScleraL_N"),
        // Eyes — right
        ("righteyeball",    "T_EyeScleraR_BC",         "T_EyeScleraR_N"),
        ("eyeright",        "T_EyeScleraR_BC",         "T_EyeScleraR_N"),
        // Teeth
        ("teeth",           "T_Teeth_BC",              "T_Teeth_N"),
        // Hair
        ("hair",            "HairCard0_Color_1K",      "HairCard0_Normal_1K"),
        // Outfit / clothing — re-use body skin texture as placeholder
        ("outfit",          "AvatarBodyFemale_Color_1K", null),
        // Eyelashes — transparent, keep as-is but reset shader
        ("eyelash",         null,                      null),
    };

    [MenuItem("Aivatar/Fix MetaHuman Materials")]
    private static void Fix()
    {
        var selection = Selection.gameObjects;
        if (selection.Length == 0)
        {
            EditorUtility.DisplayDialog("Fix MetaHuman Materials",
                "Select the MetaHuman root GameObject(s) in the Hierarchy, then run this.", "OK");
            return;
        }

        // Load all textures once
        var allTextures = AssetDatabase.FindAssets("t:Texture2D", new[] { TexturesFolder })
            .Select(guid => AssetDatabase.LoadAssetAtPath<Texture2D>(AssetDatabase.GUIDToAssetPath(guid)))
            .Where(t => t != null)
            .ToDictionary(t => t.name, t => t);

        EnsureFolder(MaterialsFolder);

        int count = 0;
        foreach (var root in selection)
        {
            foreach (var smr in root.GetComponentsInChildren<SkinnedMeshRenderer>(true))
            {
                var mats = smr.sharedMaterials;
                for (int i = 0; i < mats.Length; i++)
                {
                    var mat = mats[i];
                    if (mat == null) continue;

                    mat      = EnsureExtracted(mat, smr.gameObject.name, i);
                    mats[i]  = mat;

                    ResetShader(mat);
                    ApplyTextures(mat, allTextures);
                    EditorUtility.SetDirty(mat);
                    count++;
                }
                smr.sharedMaterials = mats;
            }
        }

        AssetDatabase.SaveAssets();
        AssetDatabase.Refresh();
        EditorUtility.DisplayDialog("Fix MetaHuman Materials",
            $"Done! Processed {count} material(s).\nCheck Console for details.", "OK");
    }

    // ── Helpers ─────────────────────────────────────────────────────────────

    private static void ResetShader(Material mat)
    {
        if (mat.shader == null ||
            mat.shader.name == "Hidden/InternalErrorShader" ||
            (!mat.shader.name.StartsWith("Standard") &&
             !mat.shader.name.StartsWith("Universal Render Pipeline") &&
             !mat.shader.name.StartsWith("HDRP") &&
             !mat.shader.name.StartsWith("Autodesk")))
        {
            Debug.Log($"[FixMetaHuman] '{mat.name}': resetting shader → Standard");
            mat.shader = Shader.Find("Standard");
        }
    }

    private static void ApplyTextures(Material mat, Dictionary<string, Texture2D> tex)
    {
        string key = mat.name.ToLower();

        foreach (var (matKey, albedoName, normalName) in Assignments)
        {
            if (!key.Contains(matKey)) continue;

            // Albedo
            if (albedoName != null && tex.TryGetValue(albedoName, out var albedo))
            {
                mat.SetTexture("_MainTex", albedo);
                Debug.Log($"[FixMetaHuman] '{mat.name}' albedo → {albedoName}");
            }
            else if (albedoName != null)
            {
                Debug.LogWarning($"[FixMetaHuman] '{mat.name}': texture '{albedoName}' not found");
            }

            // Normal
            if (normalName != null && tex.TryGetValue(normalName, out var normal))
            {
                MarkAsNormalMap(normal);
                mat.SetTexture("_BumpMap", normal);
                mat.EnableKeyword("_NORMALMAP");
                Debug.Log($"[FixMetaHuman] '{mat.name}' normal  → {normalName}");
            }

            // Special: hair needs alpha cutoff
            if (matKey == "hair")
            {
                mat.SetFloat("_Mode", 1);   // Cutout
                mat.SetFloat("_Cutoff", 0.5f);
                mat.EnableKeyword("_ALPHATEST_ON");
            }

            // Log iris texture hint for eye materials
            if (matKey == "lefteyeball" || matKey == "eyeleft")
                Debug.Log($"[FixMetaHuman] '{mat.name}': iris texture = T_EyeIrisL_BC (assign manually to a second eye material if needed)");
            if (matKey == "righteyeball" || matKey == "eyeright")
                Debug.Log($"[FixMetaHuman] '{mat.name}': iris texture = T_EyeIrisR_BC (assign manually to a second eye material if needed)");

            return; // first match wins
        }

        Debug.Log($"[FixMetaHuman] '{mat.name}': no matching rule — shader reset only");
    }

    private static Material EnsureExtracted(Material mat, string goName, int index)
    {
        string assetPath = AssetDatabase.GetAssetPath(mat);
        if (!assetPath.EndsWith(".FBX", System.StringComparison.OrdinalIgnoreCase))
            return mat;

        string matName = string.IsNullOrEmpty(mat.name) ? $"{goName}_{index}" : mat.name;
        string newPath = $"{MaterialsFolder}/{matName}.mat";

        var existing = AssetDatabase.LoadAssetAtPath<Material>(newPath);
        if (existing != null) return existing;

        var copy = new Material(mat);
        AssetDatabase.CreateAsset(copy, newPath);
        Debug.Log($"[FixMetaHuman] Extracted '{matName}' → {newPath}");
        return copy;
    }

    private static void MarkAsNormalMap(Texture2D tex)
    {
        string path = AssetDatabase.GetAssetPath(tex);
        var importer = AssetImporter.GetAtPath(path) as TextureImporter;
        if (importer != null && importer.textureType != TextureImporterType.NormalMap)
        {
            importer.textureType = TextureImporterType.NormalMap;
            importer.SaveAndReimport();
        }
    }

    private static void EnsureFolder(string path)
    {
        if (!AssetDatabase.IsValidFolder(path))
        {
            var parts = path.Split('/');
            AssetDatabase.CreateFolder(string.Join("/", parts[..^1]), parts[^1]);
        }
    }
}
