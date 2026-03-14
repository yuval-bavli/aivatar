using UnityEngine;
using UnityEditor;

public static class FixAppearanceV8
{
    [MenuItem("Aivatar/Fix Appearance V8")]
    public static string Run()
    {
        var log = new System.Text.StringBuilder();

        var browGO = FindByName("Eyebrows_M_Natural_CardsMesh_Group0_LOD0");
        if (browGO == null)
        {
            log.AppendLine("ERROR: Eyebrow mesh not found");
            return log.ToString();
        }

        // First, let's try a huge offset to prove the geometry exists
        // Push in local -Y by 2 units (should be ~2m forward in world space)
        browGO.transform.localPosition = new Vector3(0.04f, -2f, 0.04f);
        EditorUtility.SetDirty(browGO);

        log.AppendLine($"HUGE OFFSET TEST:");
        log.AppendLine($"Local pos: {browGO.transform.localPosition}");
        log.AppendLine($"World pos: {browGO.transform.position}");

        var renderer = browGO.GetComponent<Renderer>();
        if (renderer != null)
        {
            log.AppendLine($"World bounds: center={renderer.bounds.center}, size={renderer.bounds.size}");
            log.AppendLine($"Renderer enabled: {renderer.enabled}");
            log.AppendLine($"Material: {renderer.sharedMaterial?.name}");
        }

        // Keep bright red material for visibility
        var browMat = AssetDatabase.LoadAssetAtPath<Material>(
            "Assets/Models/Avatar/Materials/Eyebrows.mat");
        if (browMat != null)
        {
            browMat.SetFloat("_AlphaClip", 0f);
            browMat.DisableKeyword("_ALPHATEST_ON");
            browMat.SetFloat("_Surface", 0f);
            browMat.SetColor("_BaseColor", new Color(1f, 0f, 0f, 1f));
            browMat.SetTexture("_BaseMap", null);
            browMat.renderQueue = 2001;
            browMat.SetFloat("_Cull", 0f);
            browMat.SetFloat("_ZWrite", 1f);
            EditorUtility.SetDirty(browMat);
        }

        AssetDatabase.SaveAssets();
        string result = log.ToString();
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
