#if UNITY_EDITOR
using UnityEditor;
using UnityEngine;
using System.Collections.Generic;

/// <summary>
/// Extracts bone poses from viseme_animation.fbx at each viseme frame
/// and creates an AnimLipSyncData asset + wires AnimLipSync on Avatar.
/// </summary>
public static class AnimLipSyncSetup
{
    private static readonly string ANIM_FBX_PATH = "Assets/Models/Avatar/viseme_animation.fbx";

    private static readonly (int frame, string name)[] VISEMES =
    {
        (0, "sil"), (10, "PP"), (20, "FF"), (30, "TH"), (40, "DD"),
        (50, "kk"), (60, "CH"), (70, "SS"), (80, "nn"), (90, "RR"),
        (100, "aa"), (110, "E"), (120, "ih"), (130, "oh"), (140, "ou"),
    };

    [MenuItem("Aivatar/Setup AnimLipSync")]
    public static void Setup()
    {
        var result = Run();
        Debug.Log(result);
    }

    public static string Run()
    {
        var report = new System.Text.StringBuilder();

        // 1. Load animation clip
        AnimationClip clip = null;
        foreach (var asset in AssetDatabase.LoadAllAssetsAtPath(ANIM_FBX_PATH))
        {
            if (asset is AnimationClip c && !c.name.StartsWith("__preview__"))
            {
                clip = c;
                break;
            }
        }
        if (clip == null) return "ERROR: No AnimationClip in viseme_animation.fbx";

        float fps = clip.frameRate > 0 ? clip.frameRate : 30f;
        report.AppendLine($"Clip: '{clip.name}' fps={fps} length={clip.length:F3}s");

        // 2. Find viseme_animation root in scene
        Transform animRoot = null;
        foreach (var go in Object.FindObjectsByType<GameObject>(
            FindObjectsInactive.Include, FindObjectsSortMode.None))
        {
            if (go.name == "viseme_animation" && go.transform.parent == null)
            {
                animRoot = go.transform;
                break;
            }
        }
        if (animRoot == null) return "ERROR: viseme_animation root not found in scene";

        // 3. Find Face_LOD0 SMR to get the list of facial bones
        SkinnedMeshRenderer faceSMR = null;
        foreach (var smr in Object.FindObjectsByType<SkinnedMeshRenderer>(
            FindObjectsInactive.Include, FindObjectsSortMode.None))
        {
            string path = GetPath(smr.transform);
            if (smr.name == "Face_LOD0" && path.Contains("viseme_animation"))
            {
                faceSMR = smr;
                break;
            }
        }
        if (faceSMR == null) return "ERROR: Face_LOD0 not found under viseme_animation";

        // 4. Collect all facial bones (those with FACIAL in the name + jaw-related)
        var facialBones = new List<Transform>();
        var facialBoneNames = new List<string>();
        var seen = new HashSet<string>();

        foreach (var bone in faceSMR.bones)
        {
            if (bone == null) continue;
            string name = bone.name;
            // Include facial bones and key neck/head bones
            if (name.Contains("FACIAL") || name == "head" || name.Contains("neck") ||
                name.Contains("jaw") || name.Contains("Jaw"))
            {
                if (seen.Add(name))
                {
                    facialBones.Add(bone);
                    facialBoneNames.Add(name);
                }
            }
        }

        report.AppendLine($"Facial bones to track: {facialBones.Count}");

        // 5. Create editable clip copy for sampling
        var editableClip = Object.Instantiate(clip);
        editableClip.legacy = true;

        // Add Animation component if needed
        var animComp = animRoot.GetComponent<Animation>();
        bool addedAnim = false;
        if (animComp == null)
        {
            animComp = animRoot.gameObject.AddComponent<Animation>();
            addedAnim = true;
        }
        animComp.AddClip(editableClip, "visemes");
        animComp.clip = editableClip;

        // 6. Sample rest pose and each viseme
        int boneCount = facialBones.Count;
        int visemeCount = VISEMES.Length;
        var poses = new AnimLipSyncData.BonePose[visemeCount * boneCount];
        var visemeNames = new string[visemeCount];

        // Store rest pose
        editableClip.SampleAnimation(animRoot.gameObject, 0f);
        var restPos = new Vector3[boneCount];
        var restRot = new Quaternion[boneCount];
        for (int b = 0; b < boneCount; b++)
        {
            restPos[b] = facialBones[b].localPosition;
            restRot[b] = facialBones[b].localRotation;
        }

        for (int v = 0; v < visemeCount; v++)
        {
            int frame = VISEMES[v].frame;
            visemeNames[v] = VISEMES[v].name;
            float time = frame / fps;

            editableClip.SampleAnimation(animRoot.gameObject, time);

            int changedBones = 0;
            for (int b = 0; b < boneCount; b++)
            {
                int idx = v * boneCount + b;
                poses[idx] = new AnimLipSyncData.BonePose
                {
                    localPosition = facialBones[b].localPosition,
                    localRotation = facialBones[b].localRotation
                };

                float posDiff = (facialBones[b].localPosition - restPos[b]).magnitude;
                float rotDiff = Quaternion.Angle(facialBones[b].localRotation, restRot[b]);
                if (posDiff > 0.00001f || rotDiff > 0.01f)
                    changedBones++;
            }

            report.AppendLine($"  {VISEMES[v].name} (frame {frame}): {changedBones} bones differ from rest");
        }

        // Reset to rest
        editableClip.SampleAnimation(animRoot.gameObject, 0f);

        // Cleanup
        if (addedAnim) Object.DestroyImmediate(animComp);
        Object.DestroyImmediate(editableClip);

        // 7. Create/update AnimLipSyncData asset
        string dataPath = "Assets/Models/Avatar/AnimLipSyncData.asset";
        var data = AssetDatabase.LoadAssetAtPath<AnimLipSyncData>(dataPath);
        if (data == null)
        {
            data = ScriptableObject.CreateInstance<AnimLipSyncData>();
            AssetDatabase.CreateAsset(data, dataPath);
        }

        data.visemeNames = visemeNames;
        data.boneNames = facialBoneNames.ToArray();
        data.poses = poses;
        EditorUtility.SetDirty(data);
        AssetDatabase.SaveAssets();

        report.AppendLine($"\nSaved AnimLipSyncData: {visemeCount} visemes x {boneCount} bones = {poses.Length} poses");

        // 8. Wire AnimLipSync on Avatar
        var avatarGO = GameObject.Find("Avatar");
        if (avatarGO != null)
        {
            // Remove old lip sync components
            var oldPro = avatarGO.GetComponent<ProLipSync>();
            if (oldPro != null) Undo.DestroyObjectImmediate(oldPro);
            var oldBone = avatarGO.GetComponent<BoneLipSync>();
            if (oldBone != null) Undo.DestroyObjectImmediate(oldBone);
            var oldMesh = avatarGO.GetComponent<MeshLipSync>();
            if (oldMesh != null) Undo.DestroyObjectImmediate(oldMesh);

            var animLipSync = avatarGO.GetComponent<AnimLipSync>();
            if (animLipSync == null)
                animLipSync = Undo.AddComponent<AnimLipSync>(avatarGO);

            Undo.RecordObject(animLipSync, "Wire AnimLipSync");
            animLipSync.poseData = data;
            animLipSync.animModelRoot = animRoot;
            EditorUtility.SetDirty(animLipSync);

            var speech = avatarGO.GetComponent<AzureSpeechManager>();
            if (speech != null)
            {
                Undo.RecordObject(speech, "Wire speech");
                speech.lipSyncController = animLipSync;
                EditorUtility.SetDirty(speech);
            }

            report.AppendLine("Wired AnimLipSync on Avatar.");
        }
        else
        {
            report.AppendLine("'Avatar' not found — wire AnimLipSync manually.");
        }

        report.AppendLine("\nDone! AnimLipSync is ready.");
        return report.ToString();
    }

    private static string GetPath(Transform t)
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
