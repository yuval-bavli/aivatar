#if UNITY_EDITOR
using UnityEngine;
using UnityEditor;

public class ResetJawBones
{
    // Reset all jaw-related bones on every SMR in the scene to match the
    // reference FBX import pose.  The FBX stores rest-pose rotations, so we
    // re-import a fresh copy of the skeleton hierarchy and copy rotations.
    [MenuItem("Aivatar/Reset Jaw Bones")]
    public static string Reset()
    {
        // Load a fresh skeleton from the FBX asset to get the original bone rotations
        var prefab = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/Models/Avatar/SKM_model4_FaceMesh2.FBX");
        if (prefab == null)
            return "ERROR: Could not load FBX asset";

        // Build a lookup of bone name -> localRotation from the fresh FBX
        var lookup = new System.Collections.Generic.Dictionary<string, Quaternion>();
        foreach (var t in prefab.GetComponentsInChildren<Transform>(true))
            lookup[t.name] = t.localRotation;

        var sb = new System.Text.StringBuilder();
        int fixed_count = 0;

        foreach (var smr in Object.FindObjectsByType<SkinnedMeshRenderer>(FindObjectsInactive.Include, FindObjectsSortMode.None))
        {
            if (!smr.name.Contains("SKM_model4_FaceMesh")) continue;

            sb.AppendLine($"Checking bones on '{smr.name}':");
            foreach (var bone in smr.bones)
            {
                if (bone == null) continue;
                if (!bone.name.Contains("Jaw") && !bone.name.Contains("jaw")) continue;

                if (lookup.TryGetValue(bone.name, out var originalRot))
                {
                    if (Quaternion.Angle(bone.localRotation, originalRot) > 0.01f)
                    {
                        Undo.RecordObject(bone, "Reset Jaw Bone");
                        sb.AppendLine($"  FIXED '{bone.name}': {bone.localEulerAngles} -> {originalRot.eulerAngles}");
                        bone.localRotation = originalRot;
                        EditorUtility.SetDirty(bone);
                        fixed_count++;
                    }
                    else
                    {
                        sb.AppendLine($"  OK '{bone.name}': already at rest pose");
                    }
                }
                else
                {
                    sb.AppendLine($"  SKIP '{bone.name}': not found in FBX reference");
                }
            }
        }

        string result = $"Reset {fixed_count} jaw bones.\n{sb}";
        Debug.Log(result);
        return result;
    }
}
#endif
