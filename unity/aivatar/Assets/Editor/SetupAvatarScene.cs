#if UNITY_EDITOR
using UnityEditor;
using UnityEngine;

public static class SetupAvatarScene
{
    [MenuItem("Aivatar/Setup Avatar Scene")]
    public static void Setup()
    {
        // ── Avatar root ─────────────────────────────────────────────────────────
        var avatarGO = new GameObject("Avatar");

        // AudioSource (required by ProLipSync)
        var audio = avatarGO.AddComponent<AudioSource>();
        audio.playOnAwake = false;

        // ProLipSync — no faceMesh wired yet; wire in Inspector once you have a
        // SkinnedMeshRenderer + VisemeMapping asset.
        avatarGO.AddComponent<ProLipSync>();

        // AzureSpeechManager — credentials come from .env via EnvLoader
        var speech = avatarGO.AddComponent<AzureSpeechManager>();
        speech.lipSyncController = avatarGO.GetComponent<ProLipSync>();

        // ── Smoke-test caller ────────────────────────────────────────────────────
        var testerGO = new GameObject("AvatarTester");
        var tester   = testerGO.AddComponent<TestSpeak>();
        tester.speechManager = speech;

        // Select the root so the user can see it in the Inspector
        Selection.activeGameObject = avatarGO;

        Debug.Log("[SetupAvatarScene] Created 'Avatar' and 'AvatarTester' GameObjects. " +
                  "Press Play to run the smoke-test Speak.");
    }
}
#endif
