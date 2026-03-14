using UnityEngine;
using UnityEditor;

public static class FixEyebrowTest
{
    [MenuItem("Aivatar/Fix Eyebrow Test")]
    public static string Run()
    {
        var log = new System.Text.StringBuilder();

        var browGO = FindRendererByName("Eyebrows_M_Natural_CardsMesh_Group0_LOD0");
        if (browGO == null) return "ERROR: not found";

        // Position at face surface
        browGO.transform.localPosition = new Vector3(-0.01f, -0.02f, -0.76f);

        // Use custom shader with solid red, NO texture, NO alpha clip
        var browMat = AssetDatabase.LoadAssetAtPath<Material>(
            "Assets/Models/Avatar/Materials/Eyebrows.mat");
        var customShader = Shader.Find("Aivatar/EyebrowOverlay");

        if (browMat != null && customShader != null)
        {
            browMat.shader = customShader;
            browMat.SetTexture("_BaseMap", Texture2D.whiteTexture); // Solid white texture
            browMat.SetColor("_BaseColor", new Color(1f, 0f, 0f, 1f)); // RED
            browMat.SetFloat("_Cutoff", 0f); // No alpha clipping
            browMat.renderQueue = 2100;
            EditorUtility.SetDirty(browMat);
            log.AppendLine("Set to SOLID RED with custom shader (ZTest Always)");
        }

        // Also log the shader keywords and passes
        if (browMat != null)
        {
            log.AppendLine($"Shader: {browMat.shader.name}");
            log.AppendLine($"PassCount: {browMat.passCount}");
            for (int i = 0; i < browMat.passCount; i++)
            {
                log.AppendLine($"  Pass[{i}]: {browMat.GetPassName(i)}");
            }
        }

        EditorUtility.SetDirty(browGO);
        AssetDatabase.SaveAssets();
        return log.ToString();
    }

    static GameObject FindRendererByName(string name)
    {
        foreach (var r in Object.FindObjectsOfType<Renderer>())
            if (r.gameObject.name == name) return r.gameObject;
        return null;
    }
}
