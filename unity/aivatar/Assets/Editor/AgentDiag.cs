#if UNITY_EDITOR
using UnityEngine;
using System.Text;

public static class AgentDiag
{
    public static string Run()
    {
        var sb = new StringBuilder();

        // Find AzureSpeechManager and check lipSyncController
        var mgr = Object.FindFirstObjectByType<AzureSpeechManager>();
        if (mgr == null)
        {
            sb.AppendLine("AzureSpeechManager: NOT FOUND");
        }
        else
        {
            sb.AppendLine($"AzureSpeechManager: found on '{mgr.gameObject.name}'");
            sb.AppendLine($"  serverUrl: {mgr.serverUrl}");
            sb.AppendLine($"  lipSyncController: {(mgr.lipSyncController != null ? mgr.lipSyncController.GetType().Name + " on " + ((MonoBehaviour)mgr.lipSyncController).gameObject.name : "NULL")}");
        }

        // Find AnimClipLipSync
        var anim = Object.FindFirstObjectByType<AnimClipLipSync>();
        if (anim == null)
        {
            sb.AppendLine("AnimClipLipSync: NOT FOUND");
        }
        else
        {
            sb.AppendLine($"AnimClipLipSync: on '{anim.gameObject.name}'");
            sb.AppendLine($"  visemeClip: {(anim.visemeClip != null ? anim.visemeClip.name : "NULL")}");
            sb.AppendLine($"  animRoot: {(anim.animRoot != null ? anim.animRoot.name : "NULL")}");
            sb.AppendLine($"  smoothTime: {anim.smoothTime}");
            sb.AppendLine($"  lookAheadMs: {anim.lookAheadMs}");
        }

        // Find ProLipSync
        var pro = Object.FindFirstObjectByType<ProLipSync>();
        if (pro == null)
        {
            sb.AppendLine("ProLipSync: NOT FOUND");
        }
        else
        {
            sb.AppendLine($"ProLipSync: on '{pro.gameObject.name}' (enabled={pro.enabled})");
        }

        // Find TestSpeak
        var test = Object.FindFirstObjectByType<TestSpeak>();
        if (test != null)
        {
            sb.AppendLine($"TestSpeak: on '{test.gameObject.name}', text='{test.testText}'");
            sb.AppendLine($"  speechManager: {(test.speechManager != null ? "assigned" : "NULL")}");
        }

        return sb.ToString();
    }
}
#endif
