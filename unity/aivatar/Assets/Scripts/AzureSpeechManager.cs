using System;
using System.Collections;
using System.Text;
using UnityEngine;
using UnityEngine.Networking;

/// <summary>
/// Replaces the Azure TTS backend with the local sound_engine Python server.
/// Start the server before playing in Unity:
///   .venv/Scripts/python sound_engine/server.py
/// </summary>
public class AzureSpeechManager : MonoBehaviour
{
    [Header("Sound Engine Server")]
    public string serverUrl = "http://127.0.0.1:5123";

    [Header("References")]
    public LipSyncBase lipSyncController;

    // ── JSON DTOs ────────────────────────────────────────────────────────────

    [Serializable]
    private class SpeakRequest
    {
        public string text;
    }

    [Serializable]
    private class SentenceEventData
    {
        public string text;
        public float  end_time_ms;
    }

    [Serializable]
    private class SpeakResponse
    {
        public string                                audio_base64;
        public int                                   sample_rate;
        public float                                 duration_ms;
        public AudioVisemeDecoder.VisemeEventData[]  viseme_events;
        public SentenceEventData[]                   sentence_events;
    }

    // ── Public API ───────────────────────────────────────────────────────────

    public void Speak(string text)
    {
        StartCoroutine(SpeakCoroutine(text));
    }

    // ── Implementation ───────────────────────────────────────────────────────

    private IEnumerator SpeakCoroutine(string text)
    {
        string url  = serverUrl.TrimEnd('/') + "/speak";
        byte[] body = Encoding.UTF8.GetBytes(JsonUtility.ToJson(new SpeakRequest { text = text }));

        using var req = new UnityWebRequest(url, "POST")
        {
            uploadHandler   = new UploadHandlerRaw(body),
            downloadHandler = new DownloadHandlerBuffer(),
        };
        req.SetRequestHeader("Content-Type", "application/json");

        yield return req.SendWebRequest();

        if (req.result != UnityWebRequest.Result.Success)
        {
            Debug.LogError($"[SoundEngine] Request failed: {req.error}\n" +
                           "Make sure the server is running: .venv/Scripts/python sound_engine/server.py");
            yield break;
        }

        SpeakResponse resp;
        try
        {
            resp = JsonUtility.FromJson<SpeakResponse>(req.downloadHandler.text);
        }
        catch (Exception e)
        {
            Debug.LogError($"[SoundEngine] Failed to parse server response: {e.Message}");
            yield break;
        }

        // Decode WAV + build VisemeTimeline via shared helper
        AudioClip clip;
        VisemeTimeline timeline;
        try
        {
            (clip, timeline) = AudioVisemeDecoder.Decode(resp.audio_base64, resp.viseme_events, resp.duration_ms, text);
            if (resp.sentence_events != null)
            {
                foreach (var se in resp.sentence_events)
                    timeline.sentences.Add(new SentenceEvent { text = se.text, endTimeMs = se.end_time_ms });
            }
            Debug.Log($"[SoundEngine] Clip ready: samples={clip.samples} freq={clip.frequency} length={clip.length:F3}s");
        }
        catch (Exception e)
        {
            Debug.LogError($"[SoundEngine] Failed to decode audio: {e.Message}");
            yield break;
        }

        lipSyncController.Play(timeline, clip);
    }
}
