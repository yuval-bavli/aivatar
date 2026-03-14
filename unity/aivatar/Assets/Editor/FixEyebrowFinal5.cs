using UnityEngine;
using UnityEditor;

public static class FixEyebrowFinal5
{
    [MenuItem("Aivatar/Fix Eyebrow Final5")]
    public static string Run()
    {
        var log = new System.Text.StringBuilder();

        var browGO = FindRendererByName("Eyebrows_M_Natural_CardsMesh_Group0_LOD0");
        if (browGO == null) return "ERROR: not found";

        // Position: at face surface level
        browGO.transform.localPosition = new Vector3(-0.01f, -0.02f, -0.76f);
        EditorUtility.SetDirty(browGO);

        // Apply custom shader
        var browMat = AssetDatabase.LoadAssetAtPath<Material>(
            "Assets/Models/Avatar/Materials/Eyebrows.mat");
        var customShader = Shader.Find("Aivatar/EyebrowOverlay");
        var hairTex = AssetDatabase.LoadAssetAtPath<Texture2D>(
            "Assets/Models/Avatar/Textures/HairCard0_Color_1K.png");

        if (browMat != null && customShader != null)
        {
            browMat.shader = customShader;
            browMat.SetTexture("_BaseMap", hairTex);
            browMat.SetColor("_BaseColor", new Color(0.14f, 0.09f, 0.06f, 1f));
            browMat.SetFloat("_Cutoff", 0.03f);
            browMat.renderQueue = 2100;
            EditorUtility.SetDirty(browMat);
            log.AppendLine("Applied custom EyebrowOverlay shader");
        }
        else
        {
            log.AppendLine($"ERROR: browMat={browMat != null}, shader={customShader != null}");
            if (customShader == null)
            {
                // List available shaders containing "Aivatar"
                log.AppendLine("Trying to find shader...");
                var s = Shader.Find("Aivatar/EyebrowOverlay");
                log.AppendLine($"Shader.Find result: {s}");
            }
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
