using UnityEngine;
using UnityEditor;

/// FixHairV2 — medium dark brown with subtle highlights
/// BaseColor (0.80, 0.65, 0.50): reduces reddish cast, shows texture highlights
/// Emission (0.05, 0.03, 0.01): tiny warm lift for highlights visibility
/// Eyebrows rebaked at strength=0.25 (between too-light 0.10 and too-dark 0.50)
public static class FixHairV2
{
    [MenuItem("Aivatar/Fix Hair V2: Medium Brown + Subtle Emission")]
    public static string Run()
    {
        var mat = AssetDatabase.LoadAssetAtPath<Material>("Assets/Models/Avatar/Materials/haircut.mat");
        if (mat == null) return "ERROR: haircut.mat not found";

        var baseColor = new Color(0.80f, 0.65f, 0.50f, 1f);
        mat.SetColor("_BaseColor", baseColor);
        mat.SetColor("_Color", baseColor);
        mat.EnableKeyword("_EMISSION");
        mat.SetColor("_EmissionColor", new Color(0.05f, 0.03f, 0.01f, 1f));
        mat.globalIlluminationFlags = MaterialGlobalIlluminationFlags.RealtimeEmissive;

        EditorUtility.SetDirty(mat);
        AssetDatabase.SaveAssets();
        return "Hair: BaseColor(0.80,0.65,0.50) + Emission(0.05,0.03,0.01)";
    }
}
