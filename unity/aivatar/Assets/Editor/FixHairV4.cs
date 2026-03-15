using UnityEngine;
using UnityEditor;

/// FixHairV4 — dark warm brown + high smoothness for specular highlights
/// No emission (caused flat look); using smooth specular instead
public static class FixHairV4
{
    [MenuItem("Aivatar/Fix Hair V4: Specular Highlights")]
    public static string Run()
    {
        var mat = AssetDatabase.LoadAssetAtPath<Material>("Assets/Models/Avatar/Materials/haircut.mat");
        if (mat == null) return "ERROR: haircut.mat not found";

        // Dark warm brown — slightly lighter than reference to compensate for shadow
        var baseColor = new Color(0.68f, 0.52f, 0.37f, 1f);
        mat.SetColor("_BaseColor", baseColor);
        mat.SetColor("_Color", baseColor);

        // Disable emission (was causing flat warm glow instead of highlights)
        mat.DisableKeyword("_EMISSION");
        mat.SetColor("_EmissionColor", new Color(0f, 0f, 0f, 1f));

        // Higher smoothness = more defined specular highlight on top of hair cards
        mat.SetFloat("_Smoothness", 0.55f);
        mat.SetFloat("_Glossiness", 0.55f);

        // Slight specular highlights via spec color (not metallic)
        mat.SetFloat("_Metallic", 0f);
        mat.SetFloat("_WorkflowMode", 1f);  // Metallic workflow

        EditorUtility.SetDirty(mat);
        AssetDatabase.SaveAssets();
        return "Hair: BaseColor(0.68,0.52,0.37) + Smoothness=0.55 (no emission)";
    }
}
