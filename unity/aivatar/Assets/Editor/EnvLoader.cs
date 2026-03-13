#if UNITY_EDITOR
using System;
using System.IO;
using UnityEditor;
using UnityEngine;

// Runs automatically when the Editor loads or recompiles.
// Reads ../../.env (repo root) and pushes variables into the process environment
// so AzureSpeechManager can read them via Environment.GetEnvironmentVariable()
// without the values ever being stored in scene or project files.
[InitializeOnLoad]
public static class EnvLoader
{
    static EnvLoader()
    {
        // Application.dataPath = <project>/Assets → go up to repo root
        string envPath = Path.GetFullPath(
            Path.Combine(Application.dataPath, "../../../.env"));

        if (!File.Exists(envPath))
        {
            Debug.LogWarning($"[EnvLoader] .env not found at: {envPath}");
            return;
        }

        int loaded = 0;
        foreach (string raw in File.ReadAllLines(envPath))
        {
            string line = raw.Trim();
            if (string.IsNullOrEmpty(line) || line.StartsWith("#")) continue;

            int eq = line.IndexOf('=');
            if (eq <= 0) continue;

            string key   = line[..eq].Trim();
            string value = line[(eq + 1)..].Trim().Trim('"').Trim('\'');

            Environment.SetEnvironmentVariable(key, value);
            loaded++;
        }

        Debug.Log($"[EnvLoader] Loaded {loaded} variable(s) from {envPath}");
    }
}
#endif
