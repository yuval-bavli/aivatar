#if UNITY_EDITOR
using UnityEditor;
using UnityEngine;

public static class WireMetaHumanLipSync
{
    [MenuItem("Aivatar/Wire MetaHuman LipSync")]
    public static string Wire()
    {
        var sb = new System.Text.StringBuilder();

        // Find or create Avatar GameObject
        var avatarGO = GameObject.Find("Avatar");
        if (avatarGO == null)
        {
            // Create Avatar at scene root
            avatarGO = new GameObject("Avatar");
            avatarGO.AddComponent<AudioSource>();
            avatarGO.AddComponent<AzureSpeechManager>();
            sb.AppendLine("Created Avatar with AudioSource + AzureSpeechManager");
        }
        else
        {
            sb.AppendLine($"Found existing Avatar");
        }

        // Ensure AudioSource
        if (avatarGO.GetComponent<AudioSource>() == null)
            avatarGO.AddComponent<AudioSource>();

        // Add or get MetaHumanLipSync
        var mhls = avatarGO.GetComponent<MetaHumanLipSync>();
        if (mhls == null)
            mhls = Undo.AddComponent<MetaHumanLipSync>(avatarGO);

        // Find face SMR
        var allSMRs = Object.FindObjectsByType<SkinnedMeshRenderer>(
            FindObjectsInactive.Include, FindObjectsSortMode.None);
        SkinnedMeshRenderer bestSMR = null;
        int maxBones = 0;
        foreach (var s in allSMRs)
        {
            if (s.bones.Length > maxBones)
            {
                maxBones = s.bones.Length;
                bestSMR = s;
            }
        }

        if (bestSMR != null)
        {
            Undo.RecordObject(mhls, "Wire MetaHumanLipSync");
            mhls.faceMesh = bestSMR;
            EditorUtility.SetDirty(mhls);
            sb.AppendLine($"Set faceMesh = '{bestSMR.name}' ({bestSMR.bones.Length} bones)");
        }

        // Wire AzureSpeechManager if exists
        var speech = avatarGO.GetComponent<AzureSpeechManager>();
        if (speech != null)
        {
            Undo.RecordObject(speech, "Wire MetaHumanLipSync");
            speech.lipSyncController = mhls;
            EditorUtility.SetDirty(speech);
            sb.AppendLine("Wired AzureSpeechManager.lipSyncController = MetaHumanLipSync");
        }

        // Verify bones found
        sb.AppendLine("\nBone check:");
        string[] boneNames = {
            "FACIAL_C_Jaw", "FACIAL_C_LipLower", "FACIAL_C_LipUpper",
            "FACIAL_L_LipCorner", "FACIAL_R_LipCorner",
            "FACIAL_C_LowerLipRotation", "FACIAL_C_TeethLower", "FACIAL_C_TeethUpper"
        };
        foreach (var bn in boneNames)
        {
            bool found = false;
            foreach (var b in bestSMR.bones)
                if (b != null && b.name == bn) { found = true; break; }
            sb.AppendLine($"  {bn}: {(found ? "OK" : "MISSING")}");
        }

        Selection.activeGameObject = avatarGO;
        string result = sb.ToString();
        Debug.Log("[WireMetaHumanLipSync] " + result);
        return result;
    }

    [MenuItem("Aivatar/Test Jaw Open")]
    public static string TestJawOpen()
    {
        // Find the face SMR by name (must be the one with facial bones)
        var smrs = Object.FindObjectsByType<SkinnedMeshRenderer>(
            FindObjectsInactive.Include, FindObjectsSortMode.None);
        SkinnedMeshRenderer faceSMR = null;
        foreach (var s in smrs)
        {
            if (s.name.Contains("FaceMesh") && s.bones.Length > 100)
            { faceSMR = s; break; }
        }
        // Fallback: find the one with the most bones
        if (faceSMR == null)
        {
            int maxB = 0;
            foreach (var s in smrs)
                if (s.bones.Length > maxB) { maxB = s.bones.Length; faceSMR = s; }
        }

        if (faceSMR == null) return "No face SMR";

        // List all bones with jaw/chin in name for debug
        var debugSb = new System.Text.StringBuilder();
        debugSb.AppendLine($"Face SMR: '{faceSMR.name}' bones={faceSMR.bones.Length}");
        Transform jaw = null;
        int nullCount = 0;
        foreach (var b in faceSMR.bones)
        {
            if (b == null) { nullCount++; continue; }
            if (b.name == "FACIAL_C_Jaw") jaw = b;
        }
        debugSb.AppendLine($"  Null bones: {nullCount}, jaw found: {jaw != null}");

        if (jaw == null)
        {
            // Try finding in scene hierarchy
            var jawGO = GameObject.Find("FACIAL_C_Jaw");
            if (jawGO != null)
            {
                jaw = jawGO.transform;
                debugSb.AppendLine($"  Found via GameObject.Find");
            }
            else
            {
                return debugSb.ToString() + "\nFACIAL_C_Jaw not found anywhere";
            }
        }

        var sb = new System.Text.StringBuilder();
        sb.AppendLine($"Jaw bone: '{jaw.name}'");
        sb.AppendLine($"  localPos: {jaw.localPosition}");
        sb.AppendLine($"  localRot: {jaw.localEulerAngles}");
        sb.AppendLine($"  worldPos: {jaw.position}");

        // Rotate jaw 30 degrees on X to open mouth
        Undo.RecordObject(jaw, "Test Jaw Open");
        jaw.localRotation = jaw.localRotation * Quaternion.Euler(30, 0, 0);
        sb.AppendLine($"  After +30° X: localRot={jaw.localEulerAngles}");

        // Force repaint
        SceneView.RepaintAll();

        string result = sb.ToString();
        Debug.Log("[TestJawOpen] " + result);
        return result;
    }

    [MenuItem("Aivatar/Reset Jaw")]
    public static string ResetJaw()
    {
        var smrs = Object.FindObjectsByType<SkinnedMeshRenderer>(
            FindObjectsInactive.Include, FindObjectsSortMode.None);
        foreach (var s in smrs)
        {
            if (s.bones.Length <= 100) continue;
            foreach (var b in s.bones)
            {
                if (b != null && b.name == "FACIAL_C_Jaw")
                {
                    Undo.RecordObject(b, "Reset Jaw");
                    // Reset to bind pose - this sets to the original import rotation
                    // We need the bindposes from the mesh
                    var mesh = s.sharedMesh;
                    if (mesh != null)
                    {
                        var bindposes = mesh.bindposes;
                        int idx = System.Array.FindIndex(s.bones, x => x == b);
                        if (idx >= 0 && idx < bindposes.Length)
                        {
                            // bindpose is inverse of the bone's transform in mesh space
                            Matrix4x4 boneMatrix = bindposes[idx].inverse;
                            b.localPosition = boneMatrix.GetColumn(3);
                            b.localRotation = boneMatrix.rotation;
                            return $"Reset jaw via bindpose idx={idx}";
                        }
                    }
                    // Fallback: undo
                    return "Could not find bindpose, use Ctrl+Z";
                }
            }
        }
        return "Jaw bone not found";
    }

    [MenuItem("Aivatar/Diagnose MetaHumanLipSync")]
    public static string Diagnose()
    {
        // Check all GameObjects for MetaHumanLipSync component
        var all = Object.FindObjectsByType<MetaHumanLipSync>(
            FindObjectsInactive.Include, FindObjectsSortMode.None);
        if (all.Length == 0) return "No MetaHumanLipSync component in scene";

        var sb = new System.Text.StringBuilder();
        foreach (var mhls in all)
        {
            sb.AppendLine($"MetaHumanLipSync on '{mhls.gameObject.name}':");
            sb.AppendLine($"  faceMesh: {(mhls.faceMesh != null ? mhls.faceMesh.name + " (" + mhls.faceMesh.bones.Length + " bones)" : "NULL")}");
            sb.AppendLine($"  enabled: {mhls.enabled}");

            var speech = mhls.GetComponent<AzureSpeechManager>();
            if (speech != null)
                sb.AppendLine($"  AzureSpeechManager.lipSyncController: {(speech.lipSyncController != null ? speech.lipSyncController.GetType().Name : "NULL")}");
        }
        return sb.ToString();
    }
}
#endif
