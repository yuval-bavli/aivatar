using System;
using System.IO;
using System.Text;
using UnityEngine;

/// <summary>
/// Shared file logger for Unity. Writes to debug/logs/unity/unity_{timestamp}.log at the repo root,
/// mirroring every message to the Unity Editor console via Debug.Log.
///
/// Usage:  AivatarLogger.Log("MyTag", "message");
///         AivatarLogger.Warn("MyTag", "something odd");
///         AivatarLogger.Error("MyTag", "it broke");
/// </summary>
public static class AivatarLogger
{
    private static StreamWriter _writer;
    private static readonly object _lock = new();
    private static string _logPath = "(not opened)";

    static AivatarLogger()
    {
        try
        {
            // Application.dataPath = <repo>/unity/aivatar/Assets  →  go up 3 dirs for repo root
            var repoRoot = Path.GetFullPath(
                Path.Combine(Application.dataPath, "..", "..", ".."));
            var logDir = Path.Combine(repoRoot, "debug", "logs", "unity");
            Directory.CreateDirectory(logDir);

            var ts = DateTime.Now.ToString("yyyyMMdd_HHmmss");
            _logPath = Path.Combine(logDir, $"unity_{ts}.log");

            _writer = new StreamWriter(_logPath, append: false, Encoding.UTF8)
            {
                AutoFlush = true,
            };
            WriteRaw("INFO ", "AivatarLogger", $"Unity logging started -> {_logPath}");
        }
        catch (Exception e)
        {
            Debug.LogWarning($"[AivatarLogger] Could not open log file: {e.Message}");
        }
    }

    // ── Public API ────────────────────────────────────────────────────────────

    public static void Log(string tag, string message)
    {
        Debug.Log($"[{tag}] {message}");
        WriteRaw("INFO ", tag, message);
    }

    public static void Warn(string tag, string message)
    {
        Debug.LogWarning($"[{tag}] {message}");
        WriteRaw("WARN ", tag, message);
    }

    public static void Error(string tag, string message)
    {
        Debug.LogError($"[{tag}] {message}");
        WriteRaw("ERROR", tag, message);
    }

    public static void Error(string tag, string message, Exception ex)
    {
        Debug.LogError($"[{tag}] {message}: {ex.Message}\n{ex.StackTrace}");
        WriteRaw("ERROR", tag, $"{message}: {ex.Message}");
        WriteRaw("ERROR", tag, $"  Stack: {ex.StackTrace?.Replace("\n", "\n        ")}");
    }

    // ── Internal ──────────────────────────────────────────────────────────────

    private static void WriteRaw(string level, string tag, string message)
    {
        if (_writer == null) return;
        var line = $"{DateTime.Now:yyyy-MM-dd HH:mm:ss.fff} [{level}] {tag}: {message}";
        lock (_lock)
        {
            try { _writer.WriteLine(line); }
            catch { /* ignore write errors to avoid infinite recursion */ }
        }
    }
}
