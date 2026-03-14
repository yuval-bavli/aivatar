using UnityEngine;
using UnityEditor;

public static class FixEyebrowComplete
{
    [MenuItem("Aivatar/Fix Eyebrow Complete")]
    public static string Run()
    {
        var log = new System.Text.StringBuilder();

        // Clean up all test objects
        foreach (var name in new[] { "TEST_EYEBROW_LEFT", "TEST_EYEBROW_RIGHT", "DEBUG_BROW_CUBE", "BIG_RED_TEST" })
        {
            var go = GameObject.Find(name);
            while (go != null) { Object.DestroyImmediate(go); go = GameObject.Find(name); }
        }

        // Reduce camera near clip to allow closer objects
        var cam = Camera.main;
        if (cam != null)
        {
            cam.nearClipPlane = 0.1f;
            EditorUtility.SetDirty(cam);
            log.AppendLine($"Camera near clip set to {cam.nearClipPlane}");
        }

        // Re-enable and position eyebrow mesh
        Renderer browRenderer = null;
        foreach (var r in Object.FindObjectsOfType<Renderer>(true)) // include inactive
        {
            if (r.gameObject.name == "Eyebrows_M_Natural_CardsMesh_Group0_LOD0")
            {
                browRenderer = r;
                break;
            }
        }

        if (browRenderer == null) return "ERROR: eyebrow renderer not found";

        browRenderer.enabled = true;
        var browGO = browRenderer.gameObject;

        // Position: push well forward to clear brow ridge depth
        browGO.transform.localPosition = new Vector3(-0.01f, -0.05f, -0.76f);
        EditorUtility.SetDirty(browGO);

        log.AppendLine($"Eyebrow world bounds: center={browRenderer.bounds.center}");
        float dist = Vector3.Distance(cam.transform.position, browRenderer.bounds.center);
        log.AppendLine($"Distance from camera: {dist}");

        // Use URP/Lit (known working) with solid red for position check
        var browMat = AssetDatabase.LoadAssetAtPath<Material>(
            "Assets/Models/Avatar/Materials/Eyebrows.mat");
        var litShader = Shader.Find("Universal Render Pipeline/Lit");

        if (browMat != null && litShader != null)
        {
            browMat.shader = litShader;
            browMat.SetTexture("_BaseMap", null);
            browMat.SetTexture("_BumpMap", null);
            browMat.SetColor("_BaseColor", new Color(1f, 0f, 0f, 1f));
            browMat.SetFloat("_AlphaClip", 0f);
            browMat.DisableKeyword("_ALPHATEST_ON");
            browMat.SetFloat("_Surface", 0f);
            browMat.SetFloat("_Cull", 0f); // Double-sided
            browMat.renderQueue = 2500;
            browMat.SetFloat("_ZWrite", 1f);
            browMat.SetFloat("_Smoothness", 0f);
            browMat.SetFloat("_Metallic", 0f);
            EditorUtility.SetDirty(browMat);
            log.AppendLine("Eyebrow: URP/Lit, solid red, no alpha, double-sided");
        }

        AssetDatabase.SaveAssets();
        string result = log.ToString();
        Debug.Log(result);
        return result;
    }
}
