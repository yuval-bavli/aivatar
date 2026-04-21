using System;
using System.Text;
using UnityEngine;

/// <summary>
/// Shared helper: decodes a base64 WAV + viseme event array into an AudioClip + VisemeTimeline.
/// Used by AzureSpeechManager (TTS server path) and ConversationClient (orchestrator path).
/// </summary>
public static class AudioVisemeDecoder
{
    [Serializable]
    public class VisemeEventData
    {
        public float time_ms;
        public int   viseme_id;
    }

    /// <summary>
    /// Decode base64 WAV bytes and build a streaming AudioClip + VisemeTimeline.
    /// </summary>
    public static (AudioClip clip, VisemeTimeline timeline) Decode(
        string audioBase64,
        VisemeEventData[] visemeEvents,
        float durationMs,
        string text = "")
    {
        byte[] wavBytes = Convert.FromBase64String(audioBase64);
        (float[] samples, int sampleRate) = ParseWav(wavBytes);

        int readPos = 0;
        var buf = samples;
        var clip = AudioClip.Create("AvatarSpeech", samples.Length, 1, sampleRate, true,
            data => {
                for (int i = 0; i < data.Length; i++)
                {
                    data[i] = readPos < buf.Length ? buf[readPos] : 0f;
                    readPos++;
                }
            },
            pos => { readPos = pos; });

        var timeline = new VisemeTimeline { text = text, durationMs = durationMs };
        if (visemeEvents != null)
        {
            foreach (var ev in visemeEvents)
            {
                timeline.visemes.Add(new VisemeEvent
                {
                    timeMs     = ev.time_ms,
                    visemeId   = ev.viseme_id,
                    visemeName = ev.viseme_id.ToString(),
                });
            }
        }

        return (clip, timeline);
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
                sampleRate = BitConverter.ToInt32(wav, pos + 12);
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
