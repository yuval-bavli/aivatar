#if UNITY_EDITOR
using UnityEditor;
using UnityEngine;
using UnityEngine.UI;

public static class SetupAvatarScene
{
    [MenuItem("Aivatar/Setup Avatar Scene")]
    public static void Setup()
    {
        var lipSync = SetupAvatar();
        var client  = SetupConversationClient(lipSync);
        SetupStopButtonUI();
        SetupMicrophoneIndicator(client);
        SetupCaptionUI(client);

        var motion = lipSync != null ? lipSync.GetComponent<NaturalMotion>() : null;
        if (motion != null) motion.conversationClient = client;

        Debug.Log("[SetupAvatarScene] Scene ready. " +
                  "Start TTS server (:5123), STT server (:8765), then run: " +
                  ".venv/Scripts/python -m aivatar_app  — then press Play.");
    }

    // ── Avatar ─────────────────────────────────────────────────────────────

    private static AnimClipLipSync SetupAvatar()
    {
        var existing = GameObject.Find("Avatar");
        if (existing != null)
        {
            Debug.Log("[SetupAvatarScene] Avatar already exists — reusing.");
            return existing.GetComponent<AnimClipLipSync>();
        }

        var avatarGO = new GameObject("Avatar");
        var audio    = avatarGO.AddComponent<AudioSource>();
        audio.playOnAwake = false;

        var lipSync = avatarGO.AddComponent<AnimClipLipSync>();

        var motion = avatarGO.AddComponent<NaturalMotion>();
        motion.lipSync = lipSync;

        // Note: the legacy direct-TTS smoke-test path (AzureSpeechManager + TestSpeak)
        // is intentionally not wired into the production scene — see those scripts'
        // header comments if you need it for a quick Azure-only test.

        Selection.activeGameObject = avatarGO;
        return lipSync;
    }

    // ── ConversationClient ────────────────────────────────────────────────────

    private static ConversationClient SetupConversationClient(AnimClipLipSync lipSync)
    {
        var existing = GameObject.Find("ConversationManager");
        if (existing != null)
        {
            Debug.Log("[SetupAvatarScene] ConversationManager already exists — reusing.");
            var c = existing.GetComponent<ConversationClient>();
            if (c != null) c.lipSyncController = lipSync;
            return c;
        }

        var go     = new GameObject("ConversationManager");
        var client = go.AddComponent<ConversationClient>();
        client.lipSyncController = lipSync;

        return client;
    }

    // ── Stop button (uGUI) ───────────────────────────────────────────────────

    private static void SetupStopButtonUI()
    {
        var conversationManager = GameObject.Find("ConversationManager");
        if (conversationManager == null) return;
        var client = conversationManager.GetComponent<ConversationClient>();

        if (GameObject.Find("StopButtonCanvas") != null)
        {
            Debug.Log("[SetupAvatarScene] StopButtonCanvas already exists — skipping.");
            return;
        }

        // Canvas
        var canvasGO = new GameObject("StopButtonCanvas");
        var canvas   = canvasGO.AddComponent<Canvas>();
        canvas.renderMode = RenderMode.ScreenSpaceOverlay;
        canvasGO.AddComponent<UnityEngine.UI.CanvasScaler>();
        canvasGO.AddComponent<UnityEngine.UI.GraphicRaycaster>();

        // Button
        var btnGO = new GameObject("StopButton");
        btnGO.transform.SetParent(canvasGO.transform, false);
        var rect = btnGO.AddComponent<RectTransform>();
        rect.anchorMin = new Vector2(1, 0);
        rect.anchorMax = new Vector2(1, 0);
        rect.pivot     = new Vector2(1, 0);
        rect.anchoredPosition = new Vector2(-20, 20);
        rect.sizeDelta = new Vector2(120, 40);

        var img = btnGO.AddComponent<UnityEngine.UI.Image>();
        img.color = new Color(0.8f, 0.2f, 0.2f);

        var btn = btnGO.AddComponent<Button>();

        var stopUI = btnGO.AddComponent<StopButtonUI>();
        stopUI.conversationClient = client;

        // Label
        var labelGO = new GameObject("Label");
        labelGO.transform.SetParent(btnGO.transform, false);
        var labelRect = labelGO.AddComponent<RectTransform>();
        labelRect.anchorMin = Vector2.zero;
        labelRect.anchorMax = Vector2.one;
        labelRect.offsetMin = labelRect.offsetMax = Vector2.zero;
        var txt = labelGO.AddComponent<Text>();
        txt.text      = "Stop (Esc)";
        txt.alignment = TextAnchor.MiddleCenter;
        txt.color     = Color.white;
        txt.font      = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
    }

    // ── Microphone indicator ──────────────────────────────────────────────────

    private static void SetupMicrophoneIndicator(ConversationClient client)
    {
        if (GameObject.Find("MicrophoneIndicator") != null)
        {
            Debug.Log("[SetupAvatarScene] MicrophoneIndicator already exists — skipping.");
            return;
        }

        const string imgPath = "Assets/Images/microphone.png";

        var canvasGO = GameObject.Find("StopButtonCanvas") ?? CreateOverlayCanvas("MicCanvas");

        var go = new GameObject("MicrophoneIndicator");
        go.transform.SetParent(canvasGO.transform, false);

        var rect = go.AddComponent<RectTransform>();
        rect.anchorMin        = new Vector2(0.5f, 0f);
        rect.anchorMax        = new Vector2(0.5f, 0f);
        rect.pivot            = new Vector2(0.5f, 0f);
        rect.anchoredPosition = new Vector2(0f, 30f);
        rect.sizeDelta        = new Vector2(80f, 80f);

        go.AddComponent<CanvasGroup>();

        var tex = AssetDatabase.LoadAssetAtPath<Texture2D>(imgPath);
        if (tex == null)
            Debug.LogWarning($"[SetupAvatarScene] Could not load texture at {imgPath}");

        var indicator = go.AddComponent<MicrophoneIndicatorUI>();
        indicator.conversationClient = client;
        indicator.micTexture         = tex;
    }

    // ── Captions (thinking indicator + transcript/reply text) ────────────────

    private static void SetupCaptionUI(ConversationClient client)
    {
        if (GameObject.Find("CaptionUI") != null)
        {
            Debug.Log("[SetupAvatarScene] CaptionUI already exists — skipping.");
            return;
        }

        var canvasGO = GameObject.Find("StopButtonCanvas") ?? CreateOverlayCanvas("CaptionCanvas");

        var go = new GameObject("CaptionUI");
        go.transform.SetParent(canvasGO.transform, false);

        var rect = go.AddComponent<RectTransform>();
        rect.anchorMin        = new Vector2(0f, 0f);
        rect.anchorMax        = new Vector2(1f, 0f);
        rect.pivot            = new Vector2(0.5f, 0f);
        rect.anchoredPosition = new Vector2(0f, 120f);
        rect.sizeDelta        = new Vector2(-40f, 160f);

        var group = go.AddComponent<CanvasGroup>();
        group.alpha = 0f;

        var caption = go.AddComponent<CaptionUI>();
        caption.conversationClient = client;
    }

    private static GameObject CreateOverlayCanvas(string name)
    {
        var go     = new GameObject(name);
        var canvas = go.AddComponent<Canvas>();
        canvas.renderMode = RenderMode.ScreenSpaceOverlay;
        go.AddComponent<CanvasScaler>();
        go.AddComponent<GraphicRaycaster>();
        return go;
    }
}
#endif
