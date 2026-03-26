#if UNITY_EDITOR
using UnityEditor;
using UnityEngine;
using System.Collections.Generic;

public static class ResetFaceBones
{
    [MenuItem("Aivatar/Reset ALL Face Bones to Bindpose")]
    public static string Reset()
    {
        var smrs = Object.FindObjectsByType<SkinnedMeshRenderer>(
            FindObjectsInactive.Include, FindObjectsSortMode.None);
        SkinnedMeshRenderer faceSMR = null;
        foreach (var s in smrs)
            if (s.bones.Length > 500) { faceSMR = s; break; }

        if (faceSMR == null) return "No face SMR with >500 bones";

        var mesh = faceSMR.sharedMesh;
        if (mesh == null) return "No shared mesh";

        var bindposes = mesh.bindposes;
        var bones = faceSMR.bones;
        int resetCount = 0;

        // Reset ALL bones that have "FACIAL_" in their name
        for (int i = 0; i < bones.Length && i < bindposes.Length; i++)
        {
            if (bones[i] == null) continue;
            if (!bones[i].name.StartsWith("FACIAL_")) continue;

            Undo.RecordObject(bones[i], "Reset Face Bones");

            // bindpose is the inverse of the bone's world-to-local matrix at bind time
            // To get the local transform, we need the parent's bindpose too
            var parent = bones[i].parent;
            if (parent != null)
            {
                // Find parent's bindpose index
                int parentIdx = -1;
                for (int j = 0; j < bones.Length; j++)
                {
                    if (bones[j] == parent) { parentIdx = j; break; }
                }

                if (parentIdx >= 0 && parentIdx < bindposes.Length)
                {
                    // localMatrix = parentBindpose.inverse * boneBindpose
                    // But bindpose = bone-to-mesh inverse, so:
                    // boneWorldMatrix = bindpose.inverse
                    // localMatrix = parentWorld.inverse * boneWorld
                    Matrix4x4 boneWorld = bindposes[i].inverse;
                    Matrix4x4 parentWorld = bindposes[parentIdx].inverse;
                    Matrix4x4 localMatrix = parentWorld.inverse * boneWorld;

                    bones[i].localPosition = localMatrix.GetColumn(3);
                    bones[i].localRotation = localMatrix.rotation;
                    bones[i].localScale = localMatrix.lossyScale;
                    resetCount++;
                    continue;
                }
            }

            // Fallback: use world matrix from bindpose
            Matrix4x4 world = bindposes[i].inverse;
            bones[i].position = world.GetColumn(3);
            bones[i].rotation = world.rotation;
            resetCount++;
        }

        SceneView.RepaintAll();
        EditorApplication.QueuePlayerLoopUpdate();
        return $"Reset {resetCount} FACIAL_ bones to bindpose";
    }
}
#endif
