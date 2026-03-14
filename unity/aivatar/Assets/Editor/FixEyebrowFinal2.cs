using UnityEngine;
using UnityEditor;

public static class FixEyebrowFinal2
{
    [MenuItem("Aivatar/Fix Eyebrow Final2")]
    public static string Run()
    {
        var log = new System.Text.StringBuilder();

        var browGO = FindRendererByName("Eyebrows_M_Natural_CardsMesh_Group0_LOD0");
        if (browGO == null)
        {
            log.AppendLine("ERROR: Eyebrow mesh not found");
            return log.ToString();
        }

        // First: test with red to see exact position
        // Then we'll switch back to proper material

        // Push eyebrows up slightly (increase local Z) and keep forward depth
        browGO.transform.localPosition = new Vector3(-0.01f, -0.03f, -0.76f);
        EditorUtility.SetDirty(browGO);

        var browRenderer = browGO.GetComponent<Renderer>();
        log.AppendLine($"Eyebrow world bounds: center={browRenderer.bounds.center}");

        // Use solid red FIRST to check position
        var browMat = AssetDatabase.LoadAssetAtPath<Material>(
            "Assets/Models/Avatar/Materials/Eyebrows.mat");
        if (browMat != null)
        {
            browMat.SetTexture("_BaseMap", null);
            browMat.SetTexture("_BumpMap", null);
            browMat.SetFloat("_AlphaClip", 0f);
            browMat.DisableKeyword("_ALPHATEST_ON");
            browMat.SetColor("_BaseColor", new Color(1f, 0f, 0f, 1f));
            browMat.SetFloat("_Cull", 0f);
            browMat.SetFloat("_Surface", 0f);
            browMat.renderQueue = 2451;
            EditorUtility.SetDirty(browMat);
            log.AppendLine("Set to RED for position check");
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
