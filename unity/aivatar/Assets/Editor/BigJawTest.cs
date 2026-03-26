#if UNITY_EDITOR
using UnityEditor;
using UnityEngine;

public static class BigJawTest
{
    [MenuItem("Aivatar/Big Jaw Test")]
    public static string Test()
    {
        var sb = new System.Text.StringBuilder();

        // Find face SMR (the skinned one with 875 bones)
        var smrs = Object.FindObjectsByType<SkinnedMeshRenderer>(
            FindObjectsInactive.Include, FindObjectsSortMode.None);
        SkinnedMeshRenderer faceSMR = null;
        foreach (var s in smrs)
            if (s.bones.Length > 500) { faceSMR = s; break; }

        if (faceSMR == null) return "No face SMR with >500 bones";

        sb.AppendLine($"Face SMR: '{faceSMR.name}' path: {GetPath(faceSMR.transform)}");

        // Get jaw bone from THIS SMR's bones
        Transform jaw = null;
        int jawIdx = -1;
        for (int i = 0; i < faceSMR.bones.Length; i++)
        {
            if (faceSMR.bones[i] != null && faceSMR.bones[i].name == "FACIAL_C_Jaw")
            {
                jaw = faceSMR.bones[i];
                jawIdx = i;
                break;
            }
        }

        if (jaw == null) return "Jaw bone not found in face SMR bones";

        sb.AppendLine($"Jaw bone path: {GetPath(jaw)}");
        sb.AppendLine($"Jaw index: {jawIdx}");
        sb.AppendLine($"Before: localRot={jaw.localEulerAngles} localPos={jaw.localPosition}");

        // Try EXTREME rotation: 90 degrees
        Undo.RecordObject(jaw, "Big Jaw Test");
        jaw.localRotation = jaw.localRotation * Quaternion.Euler(90, 0, 0);
        sb.AppendLine($"After +90° X: localRot={jaw.localEulerAngles}");

        // Also try moving it down significantly
        jaw.localPosition += new Vector3(0, -0.05f, 0);
        sb.AppendLine($"After move down: localPos={jaw.localPosition}");

        // Force SMR update
        faceSMR.forceMatrixRecalculationPerRender = true;

        // Force repaint
        SceneView.RepaintAll();
        EditorApplication.QueuePlayerLoopUpdate();

        string result = sb.ToString();
        Debug.Log("[BigJawTest] " + result);
        return result;
    }

    [MenuItem("Aivatar/Undo Big Jaw Test")]
    public static string UndoTest()
    {
        Undo.PerformUndo();
        Undo.PerformUndo();
        SceneView.RepaintAll();
        EditorApplication.QueuePlayerLoopUpdate();
        return "Undone";
    }

    static string GetPath(Transform t)
    {
        string path = t.name;
        while (t.parent != null)
        {
            t = t.parent;
            path = t.name + "/" + path;
        }
        return path;
    }
}
#endif
