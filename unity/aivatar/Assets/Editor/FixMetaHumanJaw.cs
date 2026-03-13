using UnityEngine;
using UnityEditor;

/// <summary>
/// Tools → Fix MetaHuman Jaw
///
/// MetaHuman FBX exports often have the jaw bone in a wrong rest rotation,
/// causing the lower teeth geometry to appear at the top of the head.
/// This script finds jaw/teeth bones by name and resets them to closed-mouth pose.
///
/// Select the face GameObject (SKM_model4_FaceMesh) in the Hierarchy first.
/// </summary>
public static class FixMetaHumanJaw
{
    // Standard MetaHuman facial bone names that control the jaw
    private static readonly string[] JawBoneNames =
    {
        "FACIAL_C_Jaw",
        "FACIAL_C_JawRoot",
        "jaw",
        "Jaw",
        "lowerJaw",
        "LowerJaw",
    };

    [MenuItem("Tools/Fix MetaHuman Jaw")]
    private static void Fix()
    {
        var selection = Selection.gameObjects;
        if (selection.Length == 0)
        {
            EditorUtility.DisplayDialog("Fix MetaHuman Jaw",
                "Select the face mesh GameObject (SKM_model4_FaceMesh) in the Hierarchy first.", "OK");
            return;
        }

        int fixed_count = 0;

        foreach (var root in selection)
        {
            // Walk every transform in the hierarchy
            foreach (Transform t in root.GetComponentsInChildren<Transform>(true))
            {
                if (!IsJawBone(t.name)) continue;

                Undo.RecordObject(t, "Fix MetaHuman Jaw");
                t.localRotation = Quaternion.identity;
                t.localPosition = Vector3.zero;

                Debug.Log($"[JawFix] Reset bone: '{t.name}' on '{root.name}'");
                fixed_count++;
            }
        }

        if (fixed_count == 0)
        {
            // No known bone names found — dump all bone names so we can identify the right one
            Debug.LogWarning("[JawFix] No jaw bones found by known names. Listing all bones:");
            foreach (var root in selection)
            {
                var smr = root.GetComponentInChildren<SkinnedMeshRenderer>(true);
                if (smr != null && smr.bones != null)
                {
                    foreach (var bone in smr.bones)
                        if (bone != null)
                            Debug.Log($"  Bone: {bone.name}");
                }
            }
            EditorUtility.DisplayDialog("Fix MetaHuman Jaw",
                "No jaw bones found. Check the Console — all bone names are listed there.\n" +
                "Find the jaw bone name and report it so the script can be updated.", "OK");
        }
        else
        {
            EditorUtility.DisplayDialog("Fix MetaHuman Jaw",
                $"Reset {fixed_count} jaw bone(s). Check scene — teeth should now be inside the mouth.", "OK");
        }
    }

    private static bool IsJawBone(string name)
    {
        foreach (var candidate in JawBoneNames)
            if (name.Equals(candidate, System.StringComparison.OrdinalIgnoreCase))
                return true;
        return false;
    }
}
