using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;

/// FixEyelashScaleAndColor — makes eyelashes visually thinner by:
/// 1. Setting eyelash BaseColor to near-skin so they blend in (less harsh)
/// 2. Inspecting face mesh hierarchy for any standalone eyelash objects
public static class FixEyelashScaleAndColor
{
    [MenuItem("Aivatar/Fix Eyelash Appearance")]
    public static string Run()
    {
        var log = new System.Text.StringBuilder();

        // 1. Change eyelash mat BaseColor to dark-but-softer brown + reduce alpha visually
        // by switching to a semi-transparent approach
        var lashMat = AssetDatabase.LoadAssetAtPath<Material>("Assets/Models/Avatar/Materials/MI_Face_EyelashesHiLODs.mat");
        if (lashMat != null)
        {
            // Softer dark brown, less harsh than near-black
            // Also lower cutoff to blend edges more naturally
            lashMat.SetColor("_BaseColor", new Color(0.12f, 0.09f, 0.07f, 1f));
            lashMat.SetColor("_Color", new Color(0.12f, 0.09f, 0.07f, 1f));
            lashMat.SetFloat("_Cutoff", 0.92f);  // show more of the thin eroded strands
            EditorUtility.SetDirty(lashMat);
            log.Append("Eyelash color softened + cutoff=0.92. ");
        }

        // 2. Print all children of the face FBX to diagnose structure
        log.AppendLine();
        log.AppendLine("Face FBX hierarchy:");
        foreach (var r in GameObject.FindObjectsOfType<Renderer>(true))
        {
            if (r.gameObject.name == "SKM_model4_FaceMesh" ||
                r.gameObject.name.Contains("EyelashesHiLODs") ||
                r.gameObject.name.Contains("Eyelash"))
            {
                log.AppendLine($"  {r.gameObject.name}: enabled={r.enabled}, type={r.GetType().Name}");
                Transform p = r.transform.parent;
                if (p != null) log.AppendLine($"    parent: {p.name}");
            }
        }

        // 3. Check for any standalone eyelash child objects inside face FBX
        var faceMeshGOs = GameObject.FindObjectsOfType<MeshRenderer>(true);
        foreach (var r in faceMeshGOs)
        {
            if (r.gameObject.name == "SKM_model4_FaceMesh")
            {
                // Print all children
                log.AppendLine($"Children of {r.gameObject.name}:");
                for (int i = 0; i < r.transform.childCount; i++)
                    log.AppendLine($"  [{i}]: {r.transform.GetChild(i).name}");
                break;
            }
        }

        AssetDatabase.SaveAssets();
        EditorSceneManager.SaveOpenScenes();
        return log.ToString();
    }
}
