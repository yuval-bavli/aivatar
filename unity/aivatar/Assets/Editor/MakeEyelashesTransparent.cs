using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine.Rendering;

/// MakeEyelashesTransparent — switches eyelash material to transparent mode with low alpha
/// so the thick geometry becomes nearly invisible (faint natural lash look)
public static class MakeEyelashesTransparent
{
    [MenuItem("Aivatar/Make Eyelashes Transparent (faint natural look)")]
    public static string Run()
    {
        var mat = AssetDatabase.LoadAssetAtPath<Material>("Assets/Models/Avatar/Materials/MI_Face_EyelashesHiLODs.mat");
        if (mat == null) return "ERROR: material not found";

        // Switch to Transparent surface mode
        mat.SetFloat("_Surface", 1f);           // 1 = Transparent
        mat.SetFloat("_Blend", 0f);             // 0 = Alpha blend
        mat.SetFloat("_AlphaClip", 0f);         // no cutout
        mat.SetFloat("_AlphaToMask", 0f);
        mat.SetFloat("_ZWrite", 0f);
        mat.SetFloat("_SrcBlend", 5f);          // SrcAlpha
        mat.SetFloat("_DstBlend", 10f);         // OneMinusSrcAlpha
        mat.SetFloat("_SrcBlendAlpha", 1f);
        mat.SetFloat("_DstBlendAlpha", 10f);

        // Faint dark brown color, low alpha = near-invisible natural lash
        mat.SetColor("_BaseColor", new Color(0.10f, 0.07f, 0.05f, 0.22f));
        mat.SetColor("_Color", new Color(0.10f, 0.07f, 0.05f, 0.22f));

        // Remove ALPHATEST keyword, add TRANSPARENT keyword
        mat.DisableKeyword("_ALPHATEST_ON");
        mat.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");

        // Set render queue for transparent
        mat.renderQueue = (int)RenderQueue.Transparent;

        // Update RenderType tag
        mat.SetOverrideTag("RenderType", "Transparent");

        EditorUtility.SetDirty(mat);
        AssetDatabase.SaveAssets();
        EditorSceneManager.SaveOpenScenes();
        return "Eyelash material switched to Transparent mode, alpha=0.22 (faint natural look)";
    }
}
