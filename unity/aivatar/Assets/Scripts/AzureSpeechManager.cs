using System;
using System.Collections.Generic;
using System.IO;
using System.Text.RegularExpressions;
using UnityEngine;
using Microsoft.CognitiveServices.Speech;

public class AzureSpeechManager : MonoBehaviour
{
    [Header("Azure Configuration")]
    public string subscriptionKey = "YOUR_KEY";
    public string region = "YOUR_REGION";
    public string voiceName = "en-US-JennyNeural";

    [Header("References")]
    public ProLipSync lipSyncController;

    [Header("Settings")]
    [Range(0, 800)] public float pauseBetweenSentencesMs = 400f;

    // Raw 16 kHz mono PCM — matches the HTML which uses a 16 kHz Azure voice
    private const int SampleRate = 16000;

    private SpeechConfig config;

    void Awake()
    {
        string key = IsDefault(subscriptionKey) ? ReadEnv("AZURE_SPEECH_KEY")    : subscriptionKey;
        string reg = IsDefault(region)          ? ReadEnv("AZURE_SPEECH_REGION") : region;

        if (string.IsNullOrEmpty(key) || string.IsNullOrEmpty(reg))
        {
            Debug.LogError("[AzureSpeechManager] Azure key/region not set. " +
                           "Add AZURE_SPEECH_KEY and AZURE_SPEECH_REGION to your .env file.");
            return;
        }

        config = SpeechConfig.FromSubscription(key, reg);
        config.SpeechSynthesisVoiceName = voiceName;
        config.SetSpeechSynthesisOutputFormat(SpeechSynthesisOutputFormat.Raw16Khz16BitMonoPcm);
        Debug.Log("[AzureSpeechManager] Config ready.");
    }

    private static bool IsDefault(string value) =>
        string.IsNullOrEmpty(value) || value == "YOUR_KEY" || value == "YOUR_REGION";

    // Read a key from .env (repo root, two levels above Assets/) or fall back to process env vars
    private static string ReadEnv(string key)
    {
        try
        {
            string envPath = Path.GetFullPath(
                Path.Combine(Application.dataPath, "../../../.env"));

            if (File.Exists(envPath))
            {
                foreach (string raw in File.ReadAllLines(envPath))
                {
                    string line = raw.Trim();
                    if (line.StartsWith('#') || !line.Contains('=')) continue;
                    int eq = line.IndexOf('=');
                    if (line[..eq].Trim() == key)
                        return line[(eq + 1)..].Trim().Trim('"').Trim('\'');
                }
            }
        }
        catch (Exception e) { Debug.LogWarning($"[AzureSpeechManager] .env read error: {e.Message}"); }

        // Final fallback: process environment variable
        return Environment.GetEnvironmentVariable(key);
    }

    // Mirror the HTML's speak flow:
    //   1. Split on sentence boundaries (period/!/? + space) or newlines
    //   2. Synthesize each sentence, collecting visemes offset by sentenceOffsetMs
    //   3. Insert pauseBetweenSentencesMs of silence between sentences
    //   4. Build a single unified VisemeTimeline + AudioClip and hand off to ProLipSync
    public async void Speak(string text)
    {
        if (config == null)
        {
            Debug.LogError("[AzureSpeechManager] Cannot speak — config is null. " +
                           "Check that [EnvLoader] Loaded 2 variable(s) appears in the Console on startup.");
            return;
        }

        string[] sentences = Regex.Split(text.Trim(), @"(?<=[.!?])\s+|\n+");

        var unifiedTimeline = new VisemeTimeline { text = text };
        var allSamples = new List<float>();
        float sentenceOffsetMs = 0f;

        for (int i = 0; i < sentences.Length; i++)
        {
            string sentence = sentences[i].Trim();
            if (string.IsNullOrEmpty(sentence)) continue;

            if (i > 0)
            {
                // 400 ms silence gap between sentences (matches the HTML's await setTimeout 400)
                int silenceSamples = Mathf.RoundToInt(pauseBetweenSentencesMs / 1000f * SampleRate);
                for (int s = 0; s < silenceSamples; s++) allSamples.Add(0f);
                sentenceOffsetMs += pauseBetweenSentencesMs;
            }

            using var synthesizer = new SpeechSynthesizer(config, null);
            {
                // Capture offset for this sentence's viseme events (closure-safe copy)
                float localOffsetMs = sentenceOffsetMs;

                synthesizer.VisemeReceived += (s, e) =>
                {
                    unifiedTimeline.visemes.Add(new VisemeEvent
                    {
                        timeMs     = localOffsetMs + (float)e.AudioOffset / 10000f,
                        visemeId   = (int)e.VisemeId,
                        visemeName = ((int)e.VisemeId).ToString()
                    });
                };

                var result = await synthesizer.SpeakTextAsync(sentence);

                if (result.Reason == ResultReason.SynthesizingAudioCompleted)
                {
                    float[] samples = ConvertPcmToFloat(result.AudioData);
                    allSamples.AddRange(samples);

                    // Advance offset by actual audio duration so the next sentence starts correctly
                    sentenceOffsetMs += (float)result.AudioDuration.TotalMilliseconds;
                }
                else
                {
                    Debug.LogError($"[AzureSpeechManager] Synthesis failed for: \"{sentence}\"");
                }
            }
        }

        unifiedTimeline.durationMs = sentenceOffsetMs;

        // Combine all sentence audio into one clip so ProLipSync can sync via audioSource.time
        float[] finalSamples = allSamples.ToArray();
        AudioClip clip = AudioClip.Create("AzureSpeech", finalSamples.Length, 1, SampleRate, false);
        clip.SetData(finalSamples, 0);

        lipSyncController.Play(unifiedTimeline, clip);
    }

    // Raw 16-bit PCM (no WAV header) → float [-1, 1]
    private static float[] ConvertPcmToFloat(byte[] rawPcm)
    {
        float[] samples = new float[rawPcm.Length / 2];
        for (int i = 0; i < samples.Length; i++)
        {
            short bit16 = BitConverter.ToInt16(rawPcm, i * 2);
            samples[i] = bit16 / 32768.0f;
        }
        return samples;
    }
}