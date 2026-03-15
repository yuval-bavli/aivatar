using UnityEngine;
using UnityEditor;

/// FixHairEmission — enables emission on haircut.mat to brighten dark strands
/// and reduces reddish cast via BaseColor ratio adjustment
public static class FixHairEmission
{
    [MenuItem("Aivatar/Fix Hair: Emission + Color")]
    public static string Run()
    {
        var mat = AssetDatabase.LoadAssetAtPath<Material>("Assets/Models/Avatar/Materials/haircut.mat");
        if (mat == null) return "ERROR: haircut.mat not found";

        // Reduce reddish cast, let texture natural variation show through
        mat.SetColor("_BaseColor", new Color(1.0f, 0.88f, 0.75f, 1f));
        mat.SetColor("_Color", new Color(1.0f, 0.88f, 0.75f, 1f));

        // Enable emission for brightness lift — warm glow to show highlights
        mat.EnableKeyword("_EMISSION");
        mat.SetColor("_EmissionColor", new Color(0.15f, 0.10f, 0.05f, 1f));
        mat.globalIlluminationFlags = MaterialGlobalIlluminationFlags.RealtimeEmissive;

        EditorUtility.SetDirty(mat);
        AssetDatabase.SaveAssets();
        return "Hair: BaseColor (1.0, 0.88, 0.75) + Emission (0.15, 0.10, 0.05) applied";
    }
}
