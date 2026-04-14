#if UNITY_EDITOR
using System.Collections.Generic;
using UnityEngine;

/// <summary>Captures recent Debug.Log messages for the agent bridge.</summary>
public static class AgentLog
{
    static readonly List<string> _lines = new List<string>();
    const int MaxLines = 100;

    [UnityEditor.InitializeOnLoadMethod]
    [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
    static void Init()
    {
        Application.logMessageReceived -= OnLog;
        Application.logMessageReceived += OnLog;
    }

    static void OnLog(string msg, string stackTrace, LogType type)
    {
        string prefix = type == LogType.Error || type == LogType.Exception ? "ERR" :
                        type == LogType.Warning ? "WRN" : "LOG";
        _lines.Add($"[{prefix}] {msg}");
        if (_lines.Count > MaxLines)
            _lines.RemoveAt(0);
    }

    public static string Dump()
    {
        if (_lines.Count == 0) return "(no log messages captured)";
        return string.Join("\n", _lines);
    }

    public static string Clear()
    {
        _lines.Clear();
        return "Log cleared";
    }
}
#endif
