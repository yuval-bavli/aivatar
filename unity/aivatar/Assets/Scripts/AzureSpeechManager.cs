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
    private class VisemeEventData
    {
        public float time_ms;
        public int   viseme_id;
    }

    [Serializable]
    private class SpeakResponse
    {
        public string           audio_base64;
        public int              sample_rate;
        public float            duration_ms;
        public VisemeEventData[] viseme_events;
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

        // Decode WAV and build AudioClip
        AudioClip clip;
        try
        {
            byte[] wavBytes = Convert.FromBase64String(resp.audio_base64);
            (float[] samples, int sampleRate) = ParseWav(wavBytes);

            // Use stream=true so Unity pulls from our callback — SetData doesn't work in Unity 6
            int readPos = 0;
            var buf = samples; // capture for closure
            clip = AudioClip.Create("SoundEngine", samples.Length, 1, sampleRate, true,
                data => {
                    for (int i = 0; i < data.Length; i++)
                    {
                        data[i] = readPos < buf.Length ? buf[readPos] : 0f;
                        readPos++;
                    }
                },
                pos => { readPos = pos; });

            Debug.Log($"[SoundEngine] Clip created (stream=true): " +
                      $"samples={samples.Length} sampleRate={sampleRate} length={clip.length:F3}s");
        }
        catch (Exception e)
        {
            Debug.LogError($"[SoundEngine] Failed to decode audio: {e.Message}");
            yield break;
        }

        // Build VisemeTimeline
        var timeline = new VisemeTimeline { text = text, durationMs = resp.duration_ms };
        if (resp.viseme_events != null)
        {
            foreach (var ev in resp.viseme_events)
            {
                timeline.visemes.Add(new VisemeEvent
                {
                    timeMs     = ev.time_ms,
                    visemeId   = ev.viseme_id,
                    visemeName = ev.viseme_id.ToString(),
                });
            }
        }

        Debug.Log($"[SoundEngine] Clip ready: samples={clip.samples} freq={clip.frequency} " +
                  $"length={clip.length:F3}s channels={clip.channels}");

        lipSyncController.Play(timeline, clip);
    }

    // ── WAV parsing ──────────────────────────────────────────────────────────

    /// <summary>Walk RIFF chunks to find "data", return float samples + sample rate.</summary>
    private static (float[] samples, int sampleRate) ParseWav(byte[] wav)
    {
        int sampleRate = 22050;
        int dataStart  = -1;
        int dataSize   = -1;

        int pos = 12; // skip "RIFF????WAVE"
        while (pos < wav.Length - 8)
        {
            string id   = Encoding.ASCII.GetString(wav, pos, 4);
            int    size = BitConverter.ToInt32(wav, pos + 4);

            if (id == "fmt ")
            {
                sampleRate = BitConverter.ToInt32(wav, pos + 12);
            }
            else if (id == "data")
            {
                dataStart = pos + 8;
                dataSize  = size;
                break;
            }

            pos += 8 + size;
            if (size % 2 != 0) pos++; // RIFF chunk padding
        }

        if (dataStart < 0)
            throw new Exception("WAV 'data' chunk not found");

        int count = dataSize / 2;
        var samples = new float[count];
        for (int i = 0; i < count; i++)
        {
            short s = BitConverter.ToInt16(wav, dataStart + i * 2);
            samples[i] = s / 32768.0f;
        }
        return (samples, sampleRate);
    }
}
