#if UNITY_EDITOR
using UnityEditor;
using UnityEngine;
using System.Collections.Generic;

/// <summary>
/// Samples the viseme_animation.fbx animation clip at each viseme frame,
/// bakes the resulting mesh, computes vertex deltas, and creates blendshapes
/// on the textured model4 face mesh.
/// </summary>
public static class BakeVisemesFromAnimation
{
    private static readonly string ANIM_FBX_PATH = "Assets/Models/Avatar/viseme_animation.fbx";

    private static readonly (int frame, string name)[] VISEMES =
    {
        (0, "sil"), (10, "PP"), (20, "FF"), (30, "TH"), (40, "DD"),
        (50, "kk"), (60, "CH"), (70, "SS"), (80, "nn"), (90, "RR"),
        (100, "aa"), (110, "E"), (120, "ih"), (130, "oh"), (140, "ou"),
    };

    [MenuItem("Aivatar/Bake Visemes From Animation")]
    public static void Bake()
    {
        var result = Run();
        Debug.Log(result);
    }

    /// <summary>
    /// Diagnose what's in the animation clip and the scene hierarchy.
    /// </summary>
    public static string Diagnose()
    {
        var report = new System.Text.StringBuilder();

        // Load all clips from FBX
        var allAssets = AssetDatabase.LoadAllAssetsAtPath(ANIM_FBX_PATH);
        report.AppendLine($"Assets in {ANIM_FBX_PATH}: {allAssets.Length}");
        foreach (var asset in allAssets)
        {
            report.AppendLine($"  {asset.GetType().Name}: '{asset.name}'");
            if (asset is AnimationClip clip && !clip.name.StartsWith("__preview__"))
            {
                report.AppendLine($"    length={clip.length:F3}s fps={clip.frameRate} legacy={clip.legacy}");

                // Get curve bindings
                var bindings = AnimationUtility.GetCurveBindings(clip);
                report.AppendLine($"    Curve bindings: {bindings.Length}");

                // Show first 30 bindings and count unique paths
                var uniquePaths = new HashSet<string>();
                int shown = 0;
                foreach (var b in bindings)
                {
                    uniquePaths.Add(b.path);
                    if (shown < 30)
                    {
                        report.AppendLine($"      path='{b.path}' prop='{b.propertyName}' type={b.type.Name}");
                        shown++;
                    }
                }
                if (bindings.Length > 30)
                    report.AppendLine($"      ... ({bindings.Length - 30} more)");
                report.AppendLine($"    Unique paths: {uniquePaths.Count}");
                foreach (var p in uniquePaths)
                    report.AppendLine($"      '{p}'");
            }
        }

        // Show scene hierarchy of viseme_animation root
        var allSMRs = Object.FindObjectsByType<SkinnedMeshRenderer>(
            FindObjectsInactive.Include, FindObjectsSortMode.None);
        foreach (var smr in allSMRs)
        {
            string path = GetHierarchyPath(smr.transform);
            if (path.ToLower().Contains("viseme") && smr.name == "Face_LOD0")
            {
                report.AppendLine($"\nFace_LOD0 in scene:");
                report.AppendLine($"  Full path: {path}");

                // Show relative path from root
                Transform root = smr.transform;
                while (root.parent != null) root = root.parent;
                report.AppendLine($"  Root: {root.name}");

                // Show path from root to Face_LOD0
                string relPath = GetRelativePath(root, smr.transform);
                report.AppendLine($"  Relative path from root: '{relPath}'");

                // Show first 20 bones
                report.AppendLine($"  Bones ({smr.bones.Length}):");
                for (int i = 0; i < Mathf.Min(20, smr.bones.Length); i++)
                {
                    if (smr.bones[i] != null)
                    {
                        string bonePath = GetRelativePath(root, smr.bones[i]);
                        report.AppendLine($"    [{i}] {smr.bones[i].name} path='{bonePath}'");
                    }
                }
                break;
            }
        }

        return report.ToString();
    }

    public static string Run()
    {
        var report = new System.Text.StringBuilder();

        // 1. Load animation clip from viseme_animation.fbx
        AnimationClip clip = null;
        foreach (var asset in AssetDatabase.LoadAllAssetsAtPath(ANIM_FBX_PATH))
        {
            if (asset is AnimationClip c && !c.name.StartsWith("__preview__"))
            {
                clip = c;
                report.AppendLine($"Found clip: '{c.name}' length={c.length:F3}s legacy={c.legacy}");
                break;
            }
        }
        if (clip == null)
            return $"ERROR: No AnimationClip found in {ANIM_FBX_PATH}";

        // 2. Find the Face_LOD0 SMR under viseme_animation (875 bones = face)
        //    and the model4 FaceMesh SMR (the textured one)
        SkinnedMeshRenderer animFaceSMR = null;
        SkinnedMeshRenderer model4SMR = null;

        var allSMRs = Object.FindObjectsByType<SkinnedMeshRenderer>(
            FindObjectsInactive.Include, FindObjectsSortMode.None);

        foreach (var smr in allSMRs)
        {
            string path = GetHierarchyPath(smr.transform);

            // Face_LOD0 under viseme_animation hierarchy (875 bones)
            if (smr.name == "Face_LOD0" && path.ToLower().Contains("viseme"))
                animFaceSMR = smr;

            // model4 FaceMesh (not under viseme_animation)
            if (smr.name.Contains("FaceMesh") && smr.bones.Length > 100 && !path.ToLower().Contains("viseme"))
                model4SMR = smr;
        }

        if (animFaceSMR == null)
            return "ERROR: Face_LOD0 not found under viseme_animation hierarchy";
        if (model4SMR == null)
            return "ERROR: model4 FaceMesh not found in scene";

        report.AppendLine($"Animation Face SMR: '{animFaceSMR.name}' ({animFaceSMR.bones.Length} bones)");
        report.AppendLine($"Model4 SMR: '{model4SMR.name}' ({model4SMR.bones.Length} bones)");

        // 3. Find the root GameObject of the viseme_animation model
        Transform animRoot = animFaceSMR.transform;
        while (animRoot.parent != null)
            animRoot = animRoot.parent;
        report.AppendLine($"Animation root: '{animRoot.name}'");

        // 4. Check animation curve bindings to understand path structure
        var bindings = AnimationUtility.GetCurveBindings(clip);
        report.AppendLine($"Animation has {bindings.Length} curve bindings");

        // Log a few sample paths
        int sampleCount = 0;
        foreach (var b in bindings)
        {
            if (sampleCount < 5)
                report.AppendLine($"  Sample binding: path='{b.path}' prop='{b.propertyName}'");
            sampleCount++;
        }

        float fps = clip.frameRate > 0 ? clip.frameRate : 30f;
        report.AppendLine($"Clip FPS: {fps}, length: {clip.length:F3}s ({clip.length * fps:F1} frames)");

        // 5. Use legacy Animation component to sample the clip
        //    This is more reliable than AnimationMode for FBX clips
        var animComp = animRoot.gameObject.GetComponent<Animation>();
        bool addedAnim = false;
        if (animComp == null)
        {
            animComp = animRoot.gameObject.AddComponent<Animation>();
            addedAnim = true;
        }

        // Make clip legacy-compatible for Animation component
        // We need a writable copy since FBX clips are read-only
        var editableClip = Object.Instantiate(clip);
        editableClip.legacy = true;
        animComp.AddClip(editableClip, "visemes");
        animComp.clip = editableClip;

        // 6. Sample rest pose (frame 0)
        editableClip.SampleAnimation(animRoot.gameObject, 0f);

        Mesh restMesh = new Mesh();
        animFaceSMR.BakeMesh(restMesh);
        Vector3[] restVerts = restMesh.vertices;
        int vertCount = restVerts.Length;
        report.AppendLine($"Rest pose baked: {vertCount} verts");

        // Also bake a test frame to verify animation is working
        editableClip.SampleAnimation(animRoot.gameObject, 100f / fps); // frame 100 = "aa"
        Mesh testMesh = new Mesh();
        animFaceSMR.BakeMesh(testMesh);
        Vector3[] testVerts = testMesh.vertices;
        int testMoved = 0;
        float testMax = 0;
        for (int v = 0; v < vertCount; v++)
        {
            float d = (testVerts[v] - restVerts[v]).magnitude;
            if (d > 0.0001f) testMoved++;
            if (d > testMax) testMax = d;
        }
        report.AppendLine($"Test frame 100 (aa): {testMoved} verts moved, maxDelta={testMax:F5}");
        Object.DestroyImmediate(testMesh);

        // Reset to rest before proceeding
        editableClip.SampleAnimation(animRoot.gameObject, 0f);

        if (testMoved == 0)
        {
            // Animation didn't work via SampleAnimation either.
            // Try AnimationMode as fallback
            report.AppendLine("SampleAnimation produced no movement. Trying AnimationMode...");

            AnimationMode.StartAnimationMode();
            AnimationMode.BeginSampling();
            AnimationMode.SampleAnimationClip(animRoot.gameObject, clip, 100f / fps);
            AnimationMode.EndSampling();

            Mesh testMesh2 = new Mesh();
            animFaceSMR.BakeMesh(testMesh2);
            Vector3[] testVerts2 = testMesh2.vertices;
            int testMoved2 = 0;
            float testMax2 = 0;
            for (int v = 0; v < vertCount; v++)
            {
                float d = (testVerts2[v] - restVerts[v]).magnitude;
                if (d > 0.0001f) testMoved2++;
                if (d > testMax2) testMax2 = d;
            }
            report.AppendLine($"AnimationMode test: {testMoved2} verts moved, maxDelta={testMax2:F5}");
            AnimationMode.StopAnimationMode();
            Object.DestroyImmediate(testMesh2);

            if (testMoved2 == 0)
            {
                // Neither method works. Dump bone positions to check if animation affects them
                report.AppendLine("\nBone check — sampling frame 100 vs frame 0:");
                editableClip.SampleAnimation(animRoot.gameObject, 0f);
                var restBonePos = new Dictionary<string, Vector3>();
                foreach (var bone in animFaceSMR.bones)
                {
                    if (bone != null)
                        restBonePos[bone.name] = bone.localPosition;
                }

                editableClip.SampleAnimation(animRoot.gameObject, 100f / fps);
                int bonesChanged = 0;
                foreach (var bone in animFaceSMR.bones)
                {
                    if (bone != null && restBonePos.ContainsKey(bone.name))
                    {
                        float d = (bone.localPosition - restBonePos[bone.name]).magnitude;
                        if (d > 0.00001f)
                        {
                            bonesChanged++;
                            if (bonesChanged <= 10)
                                report.AppendLine($"  Bone '{bone.name}' moved {d:F5}");
                        }
                    }
                }
                report.AppendLine($"  Total bones changed: {bonesChanged}");

                // Check bone rotations too
                editableClip.SampleAnimation(animRoot.gameObject, 0f);
                var restBoneRot = new Dictionary<string, Quaternion>();
                foreach (var bone in animFaceSMR.bones)
                {
                    if (bone != null)
                        restBoneRot[bone.name] = bone.localRotation;
                }

                editableClip.SampleAnimation(animRoot.gameObject, 100f / fps);
                int rotsChanged = 0;
                foreach (var bone in animFaceSMR.bones)
                {
                    if (bone != null && restBoneRot.ContainsKey(bone.name))
                    {
                        float angle = Quaternion.Angle(bone.localRotation, restBoneRot[bone.name]);
                        if (angle > 0.01f)
                        {
                            rotsChanged++;
                            if (rotsChanged <= 10)
                                report.AppendLine($"  Bone '{bone.name}' rotated {angle:F2}°");
                        }
                    }
                }
                report.AppendLine($"  Total bone rotations changed: {rotsChanged}");
            }

            // Cleanup
            if (addedAnim) Object.DestroyImmediate(animComp);
            Object.DestroyImmediate(editableClip);
            Object.DestroyImmediate(restMesh);
            return report.ToString();
        }

        // 7. Animation works! Bake all viseme poses
        // Re-bake rest after reset
        editableClip.SampleAnimation(animRoot.gameObject, 0f);
        Object.DestroyImmediate(restMesh);
        restMesh = new Mesh();
        animFaceSMR.BakeMesh(restMesh);
        restVerts = restMesh.vertices;

        // Create target mesh
        Mesh model4Mesh = model4SMR.sharedMesh;
        bool sameVertCount = (model4Mesh != null && model4Mesh.vertexCount == vertCount);
        Mesh targetMesh;
        if (sameVertCount)
        {
            targetMesh = Object.Instantiate(model4Mesh);
            report.AppendLine("Using model4 mesh as base (same vertex count)");
        }
        else
        {
            targetMesh = Object.Instantiate(animFaceSMR.sharedMesh);
            report.AppendLine($"Using animation mesh as base (model4={model4Mesh?.vertexCount ?? -1} vs anim={vertCount})");
        }
        targetMesh.name = "FaceMesh_VisemesFromAnim";
        targetMesh.ClearBlendShapes();

        for (int i = 0; i < VISEMES.Length; i++)
        {
            int frame = VISEMES[i].frame;
            string visemeName = VISEMES[i].name;
            float time = frame / fps;

            editableClip.SampleAnimation(animRoot.gameObject, time);

            Mesh posedMesh = new Mesh();
            animFaceSMR.BakeMesh(posedMesh);
            Vector3[] posedVerts = posedMesh.vertices;

            Vector3[] deltas = new Vector3[vertCount];
            Vector3[] deltaNormals = new Vector3[vertCount];
            Vector3[] deltaTangents = new Vector3[vertCount];

            int movedCount = 0;
            float maxDelta = 0f;
            for (int v = 0; v < vertCount; v++)
            {
                deltas[v] = posedVerts[v] - restVerts[v];
                float d = deltas[v].magnitude;
                if (d > 0.0001f) movedCount++;
                if (d > maxDelta) maxDelta = d;
            }

            targetMesh.AddBlendShapeFrame(visemeName, 100f, deltas, deltaNormals, deltaTangents);
            report.AppendLine($"  [{i}] {visemeName} (frame {frame}): {movedCount} verts, maxDelta={maxDelta:F5}");

            Object.DestroyImmediate(posedMesh);
        }

        // Reset animation
        editableClip.SampleAnimation(animRoot.gameObject, 0f);

        // Cleanup
        if (addedAnim) Object.DestroyImmediate(animComp);
        Object.DestroyImmediate(editableClip);
        Object.DestroyImmediate(restMesh);

        // 8. Save mesh asset
        string assetPath = "Assets/Models/Avatar/FaceMesh_VisemesFromAnim.asset";
        var existing = AssetDatabase.LoadAssetAtPath<Mesh>(assetPath);
        if (existing != null)
            AssetDatabase.DeleteAsset(assetPath);
        AssetDatabase.CreateAsset(targetMesh, assetPath);
        AssetDatabase.SaveAssets();
        report.AppendLine($"\nSaved {targetMesh.blendShapeCount} blendshapes to {assetPath}");

        // 9. Assign to model4 SMR
        Undo.RecordObject(model4SMR, "Assign viseme blendshape mesh");
        model4SMR.sharedMesh = targetMesh;
        EditorUtility.SetDirty(model4SMR);
        report.AppendLine($"Assigned to '{model4SMR.name}'");

        // 10. Wire ProLipSync
        var avatarGO = GameObject.Find("Avatar");
        if (avatarGO != null)
            WireProLipSync(avatarGO, model4SMR, report);

        report.AppendLine("\nDone! Viseme blendshapes baked from UE animation.");
        return report.ToString();
    }

    private static void WireProLipSync(GameObject avatarGO, SkinnedMeshRenderer faceSMR,
        System.Text.StringBuilder report)
    {
        var oldBone = avatarGO.GetComponent<BoneLipSync>();
        if (oldBone != null) Undo.DestroyObjectImmediate(oldBone);
        var oldMesh = avatarGO.GetComponent<MeshLipSync>();
        if (oldMesh != null) Undo.DestroyObjectImmediate(oldMesh);

        var proLipSync = avatarGO.GetComponent<ProLipSync>();
        if (proLipSync == null)
            proLipSync = Undo.AddComponent<ProLipSync>(avatarGO);

        string mappingPath = "Assets/Model4VisemeMapping.asset";
        var mapping = AssetDatabase.LoadAssetAtPath<VisemeMapping>(mappingPath);
        if (mapping == null)
        {
            mapping = ScriptableObject.CreateInstance<VisemeMapping>();
            AssetDatabase.CreateAsset(mapping, mappingPath);
        }

        mapping.mappings = new VisemeMapping.VisemeMap[VISEMES.Length];
        for (int i = 0; i < VISEMES.Length; i++)
        {
            mapping.mappings[i] = new VisemeMapping.VisemeMap
            {
                azureId = i,
                blendShapeName = VISEMES[i].name
            };
        }
        EditorUtility.SetDirty(mapping);
        AssetDatabase.SaveAssets();

        Undo.RecordObject(proLipSync, "Wire ProLipSync");
        proLipSync.faceMesh = faceSMR;
        proLipSync.mappingProfile = mapping;
        EditorUtility.SetDirty(proLipSync);

        var speech = avatarGO.GetComponent<AzureSpeechManager>();
        if (speech != null)
        {
            Undo.RecordObject(speech, "Wire speech controller");
            speech.lipSyncController = proLipSync;
            EditorUtility.SetDirty(speech);
        }

        report.AppendLine("Wired ProLipSync on Avatar.");
    }

    private static string GetHierarchyPath(Transform t)
    {
        string path = t.name;
        while (t.parent != null)
        {
            t = t.parent;
            path = t.name + "/" + path;
        }
        return path;
    }

    private static string GetRelativePath(Transform root, Transform target)
    {
        if (target == root) return "";
        var parts = new List<string>();
        Transform t = target;
        while (t != null && t != root)
        {
            parts.Add(t.name);
            t = t.parent;
        }
        parts.Reverse();
        return string.Join("/", parts);
    }
}
#endif
