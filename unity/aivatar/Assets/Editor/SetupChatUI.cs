#if UNITY_EDITOR
using UnityEditor;
using UnityEngine;
using UnityEngine.UI;
using TMPro;
using UnityEngine.EventSystems;

public static class SetupChatUI
{
    [MenuItem("Aivatar/Setup Chat UI")]
    public static void Setup()
    {
        // ── Canvas (always create a dedicated one for chat UI) ───────────────────
        var canvasGO = new GameObject("ChatCanvas", typeof(RectTransform));
        var canvas = canvasGO.AddComponent<Canvas>();
        canvas.renderMode = RenderMode.ScreenSpaceOverlay;
        canvas.sortingOrder = 10; // always on top
        var scaler = canvasGO.AddComponent<CanvasScaler>();
        scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
        scaler.referenceResolution = new Vector2(1920, 1080);
        scaler.matchWidthOrHeight = 0.5f;
        canvasGO.AddComponent<GraphicRaycaster>();
        Undo.RegisterCreatedObjectUndo(canvasGO, "Create ChatCanvas");

        // ── EventSystem ──────────────────────────────────────────────────────────
        if (Object.FindFirstObjectByType<EventSystem>() == null)
        {
            var esGO = new GameObject("EventSystem");
            esGO.AddComponent<EventSystem>();
            esGO.AddComponent<StandaloneInputModule>();
            Undo.RegisterCreatedObjectUndo(esGO, "Create EventSystem");
        }

        // ── Bottom bar panel ─────────────────────────────────────────────────────
        var panelGO = new GameObject("ChatPanel", typeof(RectTransform));
        panelGO.transform.SetParent(canvas.transform, false);
        var panelRect = panelGO.GetComponent<RectTransform>();
        panelRect.anchorMin = new Vector2(0, 0);
        panelRect.anchorMax = new Vector2(1, 0);
        panelRect.pivot     = new Vector2(0.5f, 0);
        panelRect.sizeDelta         = new Vector2(0, 70);
        panelRect.anchoredPosition  = Vector2.zero;
        var panelImg = panelGO.AddComponent<Image>();
        panelImg.color = new Color(0, 0, 0, 0.55f);

        // ── Input field ──────────────────────────────────────────────────────────
        var inputGO = new GameObject("InputField", typeof(RectTransform));
        inputGO.transform.SetParent(panelGO.transform, false);
        var inputRect = inputGO.GetComponent<RectTransform>();
        inputRect.anchorMin  = Vector2.zero;
        inputRect.anchorMax  = Vector2.one;
        inputRect.offsetMin  = new Vector2(10, 10);
        inputRect.offsetMax  = new Vector2(-120, -10);
        var inputBg = inputGO.AddComponent<Image>();
        inputBg.color = new Color(1, 1, 1, 0.92f);
        var inputField = inputGO.AddComponent<TMP_InputField>();

        // Text Area (clips overflowing text)
        var textAreaGO = new GameObject("Text Area", typeof(RectTransform));
        textAreaGO.transform.SetParent(inputGO.transform, false);
        var textAreaRect = textAreaGO.GetComponent<RectTransform>();
        textAreaRect.anchorMin  = Vector2.zero;
        textAreaRect.anchorMax  = Vector2.one;
        textAreaRect.offsetMin  = new Vector2(6, 4);
        textAreaRect.offsetMax  = new Vector2(-6, -4);
        textAreaGO.AddComponent<RectMask2D>();

        // Placeholder
        var phGO = new GameObject("Placeholder", typeof(RectTransform));
        phGO.transform.SetParent(textAreaGO.transform, false);
        StretchFull(phGO.GetComponent<RectTransform>());
        var ph = phGO.AddComponent<TextMeshProUGUI>();
        ph.text      = "Write text here...";
        ph.color     = new Color(0.4f, 0.4f, 0.4f, 0.8f);
        ph.fontSize  = 20;
        ph.alignment = TextAlignmentOptions.MidlineLeft;

        // Input text
        var txtGO = new GameObject("Text", typeof(RectTransform));
        txtGO.transform.SetParent(textAreaGO.transform, false);
        StretchFull(txtGO.GetComponent<RectTransform>());
        var txt = txtGO.AddComponent<TextMeshProUGUI>();
        txt.text      = "";
        txt.color     = Color.black;
        txt.fontSize  = 20;
        txt.alignment = TextAlignmentOptions.MidlineLeft;

        inputField.textViewport  = textAreaRect;
        inputField.textComponent = txt;
        inputField.placeholder   = ph;
        inputField.characterLimit = 500;

        // ── Send button ──────────────────────────────────────────────────────────
        var btnGO = new GameObject("SendButton", typeof(RectTransform));
        btnGO.transform.SetParent(panelGO.transform, false);
        var btnRect = btnGO.GetComponent<RectTransform>();
        btnRect.anchorMin        = new Vector2(1, 0);
        btnRect.anchorMax        = new Vector2(1, 1);
        btnRect.pivot            = new Vector2(1, 0.5f);
        btnRect.sizeDelta        = new Vector2(105, 0);
        btnRect.anchoredPosition = new Vector2(-10, 0);
        var btnImg   = btnGO.AddComponent<Image>();
        btnImg.color = new Color(0.18f, 0.47f, 0.95f);
        var btn      = btnGO.AddComponent<Button>();
        var colors   = btn.colors;
        colors.highlightedColor = new Color(0.28f, 0.57f, 1f);
        colors.pressedColor     = new Color(0.08f, 0.30f, 0.80f);
        btn.colors = colors;

        var btnLblGO = new GameObject("Label", typeof(RectTransform));
        btnLblGO.transform.SetParent(btnGO.transform, false);
        StretchFull(btnLblGO.GetComponent<RectTransform>());
        var btnLbl       = btnLblGO.AddComponent<TextMeshProUGUI>();
        btnLbl.text      = "Send";
        btnLbl.color     = Color.white;
        btnLbl.fontSize  = 20;
        btnLbl.fontStyle = FontStyles.Bold;
        btnLbl.alignment = TextAlignmentOptions.Center;

        // ── AvatarChatUI ─────────────────────────────────────────────────────────
        var chatUI           = panelGO.AddComponent<AvatarChatUI>();
        chatUI.inputField    = inputField;
        chatUI.sendButton    = btn;
        var speech           = Object.FindFirstObjectByType<AzureSpeechManager>();
        chatUI.speechManager = speech;

        // ── Disable TestSpeak so it doesn't auto-fire ────────────────────────────
        var testSpeak = Object.FindFirstObjectByType<TestSpeak>();
        if (testSpeak != null)
        {
            testSpeak.enabled = false;
            Debug.Log("[SetupChatUI] TestSpeak disabled.");
        }

        Undo.RegisterCreatedObjectUndo(panelGO, "Create Chat UI");
        Selection.activeGameObject = panelGO;

        string wired = speech != null ? "All references wired." : "WARNING: AzureSpeechManager not found — wire it manually on ChatPanel > AvatarChatUI.";
        Debug.Log("[SetupChatUI] Chat UI ready. " + wired);
    }

    static void StretchFull(RectTransform rt)
    {
        rt.anchorMin  = Vector2.zero;
        rt.anchorMax  = Vector2.one;
        rt.sizeDelta  = Vector2.zero;
        rt.offsetMin  = Vector2.zero;
        rt.offsetMax  = Vector2.zero;
    }
}
#endif
