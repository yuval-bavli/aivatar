using UnityEngine;
using UnityEditor;

public static class FinalCleanup
{
    [MenuItem("Aivatar/Final Cleanup")]
    public static string Run()
    {
        var log = new System.Text.StringBuilder();

        // Remove test objects
        foreach (var name in new[] { "TEST_EYEBROW_LEFT", "TEST_EYEBROW_RIGHT", "DEBUG_BROW_CUBE", "BIG_RED_TEST" })
        {
            var go = GameObject.Find(name);
            while (go != null)
            {
                Object.DestroyImmediate(go);
                log.AppendLine($"Removed {name}");
                go = GameObject.Find(name);
            }
        }

        // Ensure camera near clip is reasonable
        var cam = Camera.main;
        if (cam != null)
        {
            cam.nearClipPlane = 0.1f;
            EditorUtility.SetDirty(cam);
        }

        // Verify all key materials are in good state
        log.AppendLine("\n=== Final Material State ===");

        // Hair
        var hairMat = AssetDatabase.LoadAssetAtPath<Material>("Assets/Models/Avatar/Materials/haircut.mat");
        if (hairMat != null)
            log.AppendLine($"Hair: color={hairMat.GetColor("_BaseColor")}, cutoff={hairMat.GetFloat("_Cutoff")}, smoothness={hairMat.GetFloat("_Smoothness")}");

        // Eyebrows
        var browMat = AssetDatabase.LoadAssetAtPath<Material>("Assets/Models/Avatar/Materials/Eyebrows.mat");
        if (browMat != null)
            log.AppendLine($"Eyebrows: color={browMat.GetColor("_BaseColor")}, cutoff={browMat.GetFloat("_Cutoff")}, shader={browMat.shader.name}");

        // Eyelashes
        var lashMat = AssetDatabase.LoadAssetAtPath<Material>("Assets/Models/Avatar/Materials/MI_Face_EyelashesHiLODs.mat");
        if (lashMat != null)
            log.AppendLine($"Eyelashes: color={lashMat.GetColor("_BaseColor")}, cutoff={lashMat.GetFloat("_Cutoff")}");

        // Verify renderers
        log.AppendLine("\n=== Active Renderers ===");
        foreach (var r in Object.FindObjectsOfType<Renderer>())
        {
            log.AppendLine($"  {r.gameObject.name}: enabled={r.enabled}, mats={r.sharedMaterials.Length}");
        }

        // Mark scene dirty so changes persist
        UnityEditor.SceneManagement.EditorSceneManager.MarkSceneDirty(
            UnityEditor.SceneManagement.EditorSceneManager.GetActiveScene());

        AssetDatabase.SaveAssets();
        string result = log.ToString();
        Debug.Log(result);
        return result;
    }
}
