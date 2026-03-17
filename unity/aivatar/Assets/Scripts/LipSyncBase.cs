using UnityEngine;

// Common base so AzureSpeechManager can drive either ProLipSync (blendshapes)
// or BoneLipSync (bone rotations) without knowing the implementation.
[RequireComponent(typeof(AudioSource))]
public abstract class LipSyncBase : MonoBehaviour
{
    public abstract void Play(VisemeTimeline timeline, AudioClip clip);
}
