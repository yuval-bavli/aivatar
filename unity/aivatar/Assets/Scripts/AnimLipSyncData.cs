using UnityEngine;

/// <summary>
/// Stores pre-baked bone poses for each viseme, extracted from the UE animation clip.
/// Created by AnimLipSyncSetup editor script.
/// </summary>
[CreateAssetMenu(menuName = "Aivatar/AnimLipSync Data")]
public class AnimLipSyncData : ScriptableObject
{
    [System.Serializable]
    public struct BonePose
    {
        public Vector3 localPosition;
        public Quaternion localRotation;
    }

    public string[] visemeNames;
    public string[] boneNames;

    // Flattened array: [visemeIndex * boneCount + boneIndex]
    public BonePose[] poses;

    public int visemeCount => visemeNames != null ? visemeNames.Length : 0;
    public int boneCount => boneNames != null ? boneNames.Length : 0;

    public BonePose GetPose(int visemeIndex, int boneIndex)
    {
        int idx = visemeIndex * boneCount + boneIndex;
        if (idx < 0 || idx >= poses.Length)
            return new BonePose { localPosition = Vector3.zero, localRotation = Quaternion.identity };
        return poses[idx];
    }
}
