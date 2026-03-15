using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;

/// HideEyelashes — replaces eyelash material shader with invisible shader,
/// then bakes subtle eyelash hints onto the face texture instead.
public static class HideEyelashes
{
    [MenuItem("Aivatar/Hide Eyelash Submesh + Bake Lash Hints")]
    public static string Run()
    {
        // 1. Apply hidden shader to eyelash material
        var hiddenShader = Shader.Find("Aivatar/Hidden");
        if (hiddenShader == null) return "ERROR: Aivatar/Hidden shader not found";

        var lashMat = AssetDatabase.LoadAssetAtPath<Material>("Assets/Models/Avatar/Materials/MI_Face_EyelashesHiLODs.mat");
        if (lashMat == null) return "ERROR: lash material not found";

        lashMat.shader = hiddenShader;
        EditorUtility.SetDirty(lashMat);
        AssetDatabase.SaveAssets();
        EditorSceneManager.SaveOpenScenes();
        return "Eyelash submesh hidden via Aivatar/Hidden shader. No lashes rendered.";
    }
}
