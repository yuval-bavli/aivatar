using UnityEngine;
using UnityEditor;

public static class FixEyebrowComplete4
{
    [MenuItem("Aivatar/Fix Eyebrow Complete4")]
    public static string Run()
    {
        var log = new System.Text.StringBuilder();

        Renderer browRenderer = null;
        foreach (var r in Object.FindObjectsOfType<Renderer>(true))
            if (r.gameObject.name == "Eyebrows_M_Natural_CardsMesh_Group0_LOD0")
            { browRenderer = r; break; }
        if (browRenderer == null) return "ERROR: not found";

        browRenderer.enabled = true;
        var browGO = browRenderer.gameObject;

        // Position: raised to eyebrow level, moderate forward push
        browGO.transform.localPosition = new Vector3(-0.01f, -0.04f, -0.757f);
        EditorUtility.SetDirty(browGO);

        log.AppendLine($"Eyebrow world bounds: center={browRenderer.bounds.center}");

        // Material: higher cutoff for thinner, more natural eyebrow strands
        var browMat = AssetDatabase.LoadAssetAtPath<Material>(
            "Assets/Models/Avatar/Materials/Eyebrows.mat");
        var litShader = Shader.Find("Universal Render Pipeline/Lit");
        var hairTex = AssetDatabase.LoadAssetAtPath<Texture2D>(
            "Assets/Models/Avatar/Textures/HairCard0_Color_1K.png");
        var hairNorm = AssetDatabase.LoadAssetAtPath<Texture2D>(
            "Assets/Models/Avatar/Textures/HairCard0_Normal_1K.jpg");

        if (browMat != null && litShader != null)
        {
            browMat.shader = litShader;
            browMat.SetTexture("_BaseMap", hairTex);
            browMat.SetTexture("_BumpMap", hairNorm);
            browMat.EnableKeyword("_NORMALMAP");
            browMat.SetColor("_BaseColor", new Color(0.16f, 0.10f, 0.07f, 1f));
            browMat.SetFloat("_AlphaClip", 1f);
            browMat.EnableKeyword("_ALPHATEST_ON");
            browMat.SetFloat("_Cutoff", 0.5f); // Very high cutoff for subtle, natural eyebrows
            browMat.SetFloat("_Smoothness", 0.15f);
            browMat.SetFloat("_Cull", 0f);
            browMat.SetFloat("_Surface", 0f);
            browMat.renderQueue = 2500;
            browMat.SetFloat("_ZWrite", 1f);
            browMat.SetFloat("_Metallic", 0f);
            EditorUtility.SetDirty(browMat);
            log.AppendLine("Applied material with cutoff=0.2");
        }

        AssetDatabase.SaveAssets();
        return log.ToString();
    }
}
