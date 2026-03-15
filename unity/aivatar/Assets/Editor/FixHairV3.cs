using UnityEngine;
using UnityEditor;

/// FixHairV3 — darker chestnut brown + higher smoothness for natural highlights
public static class FixHairV3
{
    [MenuItem("Aivatar/Fix Hair V3: Darker Brown + Smoothness")]
    public static string Run()
    {
        var mat = AssetDatabase.LoadAssetAtPath<Material>("Assets/Models/Avatar/Materials/haircut.mat");
        if (mat == null) return "ERROR: haircut.mat not found";

        // Slightly darker, rich dark chestnut — but not too dark
        var baseColor = new Color(0.65f, 0.50f, 0.36f, 1f);
        mat.SetColor("_BaseColor", baseColor);
        mat.SetColor("_Color", baseColor);

        // Add subtle emission for highlight visibility
        mat.EnableKeyword("_EMISSION");
        mat.SetColor("_EmissionColor", new Color(0.06f, 0.04f, 0.02f, 1f));
        mat.globalIlluminationFlags = MaterialGlobalIlluminationFlags.RealtimeEmissive;

        // Higher smoothness to show specular highlights on hair cards
        mat.SetFloat("_Smoothness", 0.35f);
        mat.SetFloat("_Glossiness", 0.35f);

        EditorUtility.SetDirty(mat);
        AssetDatabase.SaveAssets();
        return "Hair: BaseColor(0.65,0.50,0.36) + Emission(0.06,0.04,0.02) + Smoothness=0.35";
    }
}
