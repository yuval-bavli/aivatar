using System;
using UnityEngine;

// Common base so AzureSpeechManager can drive either ProLipSync (blendshapes)
// or BoneLipSync (bone rotations) without knowing the implementation.
[RequireComponent(typeof(AudioSource))]
public abstract class LipSyncBase : MonoBehaviour
{
    /// <summary>
    /// Fired when a sentence finishes playing. Argument is the sentence text.
    /// Subscribe to feed complete sentences to an AI agent.
    /// </summary>
    public Action<string> OnSentenceFinished;

    public abstract void Play(VisemeTimeline timeline, AudioClip clip);
}
