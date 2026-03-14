using UnityEngine;
using UnityEditor;

public static class FixEyebrowFinal
{
    [MenuItem("Aivatar/Fix Eyebrow Final")]
    public static string Run()
    {
        var log = new System.Text.StringBuilder();

        var browGO = FindRendererByName("Eyebrows_M_Natural_CardsMesh_Group0_LOD0");
        if (browGO == null)
        {
            log.AppendLine("ERROR: Eyebrow mesh not found");
            return log.ToString();
        }

        // Move eyebrows down by 0.08 world units (local Z maps to world Y)
        // Current local pos: (-0.01, 0.00, -0.72)
        // Also push slightly more forward (-Y) for depth clearance
        browGO.transform.localPosition = new Vector3(-0.01f, -0.02f, -0.82f);
        EditorUtility.SetDirty(browGO);

        var browRenderer = browGO.GetComponent<Renderer>();
        log.AppendLine($"Eyebrow world bounds: center={browRenderer.bounds.center}, size={browRenderer.bounds.size}");

        // Restore proper eyebrow material
        var browMat = AssetDatabase.LoadAssetAtPath<Material>(
            "Assets/Models/Avatar/Materials/Eyebrows.mat");
        var hairTex = AssetDatabase.LoadAssetAtPath<Texture2D>(
            "Assets/Models/Avatar/Textures/HairCard0_Color_1K.png");
        var hairNorm = AssetDatabase.LoadAssetAtPath<Texture2D>(
            "Assets/Models/Avatar/Textures/HairCard0_Normal_1K.jpg");

        if (browMat != null)
        {
            browMat.SetTexture("_BaseMap", hairTex);
            browMat.SetTexture("_BumpMap", hairNorm);
            browMat.EnableKeyword("_NORMALMAP");
            browMat.SetColor("_BaseColor", new Color(0.16f, 0.10f, 0.07f, 1f)); // Dark brown
            browMat.SetFloat("_AlphaClip", 1f);
            browMat.EnableKeyword("_ALPHATEST_ON");
            browMat.SetFloat("_Cutoff", 0.03f); // Very low to show all hair strands
            browMat.SetFloat("_Smoothness", 0.15f);
            browMat.SetFloat("_Cull", 0f); // Double-sided
            browMat.SetFloat("_Surface", 0f); // Opaque
            browMat.renderQueue = 2451;
            browMat.SetFloat("_ZWrite", 1f);
            EditorUtility.SetDirty(browMat);
            log.AppendLine("Eyebrow material restored to hair card texture");
        }

        AssetDatabase.SaveAssets();
        string result = log.ToString();
        Debug.Log(result);
        return result;
    }

    static GameObject FindRendererByName(string name)
    {
        foreach (var r in Object.FindObjectsOfType<Renderer>())
        {
            if (r.gameObject.name == name) return r.gameObject;
        }
        return null;
    }
}
