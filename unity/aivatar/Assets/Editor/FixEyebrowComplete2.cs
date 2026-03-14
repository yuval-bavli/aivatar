using UnityEngine;
using UnityEditor;

public static class FixEyebrowComplete2
{
    [MenuItem("Aivatar/Fix Eyebrow Complete2")]
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

        // Lower eyebrows: decrease local Z by 0.05 to lower world Y
        // Also keep forward push at -0.05
        browGO.transform.localPosition = new Vector3(-0.01f, -0.05f, -0.81f);
        EditorUtility.SetDirty(browGO);

        log.AppendLine($"Eyebrow world bounds: center={browRenderer.bounds.center}");

        // Switch to proper hair card material
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
            browMat.SetColor("_BaseColor", new Color(0.14f, 0.09f, 0.06f, 1f)); // Dark brown
            browMat.SetFloat("_AlphaClip", 1f);
            browMat.EnableKeyword("_ALPHATEST_ON");
            browMat.SetFloat("_Cutoff", 0.03f);
            browMat.SetFloat("_Smoothness", 0.15f);
            browMat.SetFloat("_Cull", 0f); // Double-sided
            browMat.SetFloat("_Surface", 0f); // Opaque
            browMat.renderQueue = 2500;
            browMat.SetFloat("_ZWrite", 1f);
            browMat.SetFloat("_Metallic", 0f);
            EditorUtility.SetDirty(browMat);
            log.AppendLine("Applied hair card texture material to eyebrows");
        }

        AssetDatabase.SaveAssets();
        string result = log.ToString();
        Debug.Log(result);
        return result;
    }
}
