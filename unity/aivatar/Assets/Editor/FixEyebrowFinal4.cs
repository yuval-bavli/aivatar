using UnityEngine;
using UnityEditor;
using UnityEngine.Rendering;

public static class FixEyebrowFinal4
{
    [MenuItem("Aivatar/Fix Eyebrow Final4")]
    public static string Run()
    {
        var log = new System.Text.StringBuilder();

        var browGO = FindRendererByName("Eyebrows_M_Natural_CardsMesh_Group0_LOD0");
        if (browGO == null) return "ERROR: not found";

        // Reset position: keep the Y/Z correction but minimal forward push
        // Local Z → World Y, Local -Y → World -Z (toward camera)
        browGO.transform.localPosition = new Vector3(-0.01f, -0.02f, -0.76f);
        EditorUtility.SetDirty(browGO);

        var browRenderer = browGO.GetComponent<Renderer>();
        log.AppendLine($"Eyebrow world bounds: center={browRenderer.bounds.center}");

        // Configure material with ZTest Always to bypass depth occlusion
        var browMat = AssetDatabase.LoadAssetAtPath<Material>(
            "Assets/Models/Avatar/Materials/Eyebrows.mat");
        var hairTex = AssetDatabase.LoadAssetAtPath<Texture2D>(
            "Assets/Models/Avatar/Textures/HairCard0_Color_1K.png");
        var hairNorm = AssetDatabase.LoadAssetAtPath<Texture2D>(
            "Assets/Models/Avatar/Textures/HairCard0_Normal_1K.jpg");

        if (browMat != null)
        {
            // Restore hair card texture
            browMat.SetTexture("_BaseMap", hairTex);
            browMat.SetTexture("_BumpMap", hairNorm);
            browMat.EnableKeyword("_NORMALMAP");
            browMat.SetColor("_BaseColor", new Color(0.14f, 0.09f, 0.06f, 1f));
            browMat.SetFloat("_AlphaClip", 1f);
            browMat.EnableKeyword("_ALPHATEST_ON");
            browMat.SetFloat("_Cutoff", 0.03f);
            browMat.SetFloat("_Smoothness", 0.15f);
            browMat.SetFloat("_Cull", 0f); // Double-sided
            browMat.SetFloat("_Surface", 0f); // Opaque

            // KEY FIX: Set ZTest to Always so eyebrows render on top of face
            browMat.SetInt("_ZTest", (int)CompareFunction.Always);
            // Don't write to depth buffer (avoid blocking hair behind eyebrows)
            browMat.SetFloat("_ZWrite", 0f);
            // Render after face skin (queue 2000) but before hair (2450)
            browMat.renderQueue = 2100;

            EditorUtility.SetDirty(browMat);
            log.AppendLine("Set ZTest=Always, ZWrite=0 for eyebrow material");
        }

        AssetDatabase.SaveAssets();
        string result = log.ToString();
        Debug.Log(result);
        return result;
    }

    static GameObject FindRendererByName(string name)
    {
        foreach (var r in Object.FindObjectsOfType<Renderer>())
            if (r.gameObject.name == name) return r.gameObject;
        return null;
    }
}
