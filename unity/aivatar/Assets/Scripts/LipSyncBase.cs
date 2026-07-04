using System;
using UnityEngine;

// Common base so ConversationClient and AzureSpeechManager can drive an
// AnimClipLipSync (or future implementations) without knowing the details.
[RequireComponent(typeof(AudioSource))]
public abstract class LipSyncBase : MonoBehaviour
{
    /// <summary>
    /// Fired when a sentence finishes playing. Argument is the sentence text.
    /// Subscribe to feed complete sentences to an AI agent.
    /// </summary>
    public Action<string> OnSentenceFinished;

    public abstract void Play(VisemeTimeline timeline, AudioClip clip);

    /// <summary>
    /// Tells the lip sync whether another segment is already queued to play next.
    /// When true, implementations may hold the mouth pose at the end of this clip
    /// instead of decaying to rest, so back-to-back segments don't visibly pulse
    /// open→rest→open at the seam. Default no-op for implementations that don't queue.
    /// </summary>
    public virtual void SetMoreSegmentsQueued(bool moreQueued) { }
}
