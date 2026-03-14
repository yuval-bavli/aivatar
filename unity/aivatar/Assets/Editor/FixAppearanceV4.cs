using UnityEngine;
using UnityEditor;
using System.IO;

public static class FixAppearanceV4
{
    [MenuItem("Aivatar/Fix Appearance V4")]
    public static string Run()
    {
        var log = new System.Text.StringBuilder();

        // ============================================================
        // 1. HAIR: Even denser, warmer brown, less reflection
        // ============================================================
        var hairMat = AssetDatabase.LoadAssetAtPath<Material>(
            "Assets/Models/Avatar/Materials/haircut.mat");
        if (hairMat != null)
        {
            // Warm dark brown
            hairMat.SetColor("_BaseColor", new Color(0.18f, 0.12f, 0.08f, 1f));
            // Absolute minimum cutoff for maximum density
            hairMat.SetFloat("_Cutoff", 0.04f);
            // Less smoothness to reduce blue skybox reflections
            hairMat.SetFloat("_Smoothness", 0.30f);
            // Reduce metallic/specular highlights
            if (hairMat.HasProperty("_Metallic"))
                hairMat.SetFloat("_Metallic", 0f);
            // Ensure proper specular for hair
            if (hairMat.HasProperty("_SpecularHighlights"))
                hairMat.SetFloat("_SpecularHighlights", 0f);
            hairMat.DisableKeyword("_SPECULARHIGHLIGHTS_ON");
            // Reduce env reflections to avoid blue tint from skybox
            hairMat.DisableKeyword("_ENVIRONMENTREFLECTIONS_ON");
            if (hairMat.HasProperty("_EnvironmentReflections"))
                hairMat.SetFloat("_EnvironmentReflections", 0f);
            EditorUtility.SetDirty(hairMat);
            log.AppendLine("FIXED: Hair tweaked for warmth and density");
        }

        // ============================================================
        // 2. EYEBROWS: Try even lower cutoff and check geometry
        // ============================================================
        var browMat = AssetDatabase.LoadAssetAtPath<Material>(
            "Assets/Models/Avatar/Materials/Eyebrows.mat");
        var browGO = FindByName("Eyebrows_M_Natural_CardsMesh_Group0_LOD0");
        if (browGO != null && browMat != null)
        {
            var browRenderer = browGO.GetComponent<MeshRenderer>();
            var mf = browGO.GetComponent<MeshFilter>();

            if (mf != null && mf.sharedMesh != null)
            {
                var mesh = mf.sharedMesh;
                var bounds = mesh.bounds;
                log.AppendLine($"Eyebrow mesh bounds: center={bounds.center}, size={bounds.size}");
                log.AppendLine($"Eyebrow mesh verts={mesh.vertexCount}, tris={mesh.triangles.Length / 3}");

                // Check UVs
                var uvs = mesh.uv;
                if (uvs != null && uvs.Length > 0)
                {
                    Vector2 uvMin = uvs[0], uvMax = uvs[0];
                    for (int i = 1; i < uvs.Length; i++)
                    {
                        uvMin = Vector2.Min(uvMin, uvs[i]);
                        uvMax = Vector2.Max(uvMax, uvs[i]);
                    }
                    log.AppendLine($"Eyebrow UV range: min={uvMin}, max={uvMax}");
                }
            }

            // Darken eyebrows more for better visibility
            browMat.SetColor("_BaseColor", new Color(0.14f, 0.09f, 0.06f, 1f));
            browMat.SetFloat("_Cutoff", 0.03f); // Extremely low
            browMat.SetFloat("_Smoothness", 0.1f);
            browMat.DisableKeyword("_SPECULARHIGHLIGHTS_ON");
            browMat.DisableKeyword("_ENVIRONMENTREFLECTIONS_ON");
            EditorUtility.SetDirty(browMat);
            log.AppendLine("FIXED: Eyebrows darkened further");

            // Verify renderer position in world space
            if (browRenderer != null)
            {
                log.AppendLine($"Eyebrow world pos: {browGO.transform.position}");
                log.AppendLine($"Eyebrow world bounds: {browRenderer.bounds.center}, size={browRenderer.bounds.size}");
            }
        }

        // ============================================================
        // 3. Face mesh: verify material mapping is still correct
        // ============================================================
        var faceGO = FindByName("SKM_model4_FaceMesh");
        if (faceGO != null)
        {
            var faceRenderers = faceGO.GetComponents<Renderer>();
            foreach (var r in faceRenderers)
            {
                if (r is MeshRenderer mr)
                {
                    var mats = mr.sharedMaterials;
                    log.AppendLine($"\nFace mesh materials ({mats.Length}):");
                    for (int i = 0; i < mats.Length; i++)
                    {
                        log.AppendLine($"  [{i}] {(mats[i] != null ? mats[i].name : "NULL")}");
                    }
                }
            }
        }

        // ============================================================
        // 4. EYELASHES: Also remove env reflections
        // ============================================================
        var lashMat = AssetDatabase.LoadAssetAtPath<Material>(
            "Assets/Models/Avatar/Materials/MI_Face_EyelashesHiLODs.mat");
        if (lashMat != null)
        {
            lashMat.DisableKeyword("_SPECULARHIGHLIGHTS_ON");
            lashMat.DisableKeyword("_ENVIRONMENTREFLECTIONS_ON");
            lashMat.SetFloat("_Smoothness", 0.15f);
            EditorUtility.SetDirty(lashMat);
            log.AppendLine("FIXED: Eyelashes env reflections removed");
        }

        AssetDatabase.SaveAssets();
        string result = log.ToString();

        // Write to file for reading
        string path = Path.Combine(Application.dataPath, "..", "fixv4_result.txt");
        File.WriteAllText(path, result);
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
