using UnityEngine;
using UnityEngine.UI;

/// <summary>
/// Bottom-of-screen captions: shows what the user said (while thinking) and what the
/// avatar is currently saying (per speak segment), plus an animated "thinking…" indicator.
/// Built programmatically, following the MicrophoneIndicatorUI pattern, so SetupAvatarScene
/// can wire it without manual scene editing.
/// </summary>
[RequireComponent(typeof(CanvasGroup))]
public class CaptionUI : MonoBehaviour
{
    public ConversationClient conversationClient;

    [Range(0f, 1f)] public float backgroundAlpha = 0.55f;
    public float                 dotsSpeed       = 2.5f;

    private CanvasGroup _group;
    private Text        _userText;
    private Text        _avatarText;
    private bool         _thinking;

    private void Awake()
    {
        _group = GetComponent<CanvasGroup>();
        BuildUI();
    }

    private void BuildUI()
    {
        var bgGO = new GameObject("Background");
        bgGO.transform.SetParent(transform, false);
        var bgRect = bgGO.AddComponent<RectTransform>();
        bgRect.anchorMin = Vector2.zero;
        bgRect.anchorMax = Vector2.one;
        bgRect.offsetMin = bgRect.offsetMax = Vector2.zero;
        var bgImg = bgGO.AddComponent<Image>();
        bgImg.color = new Color(0f, 0f, 0f, backgroundAlpha);

        _userText = CreateLabel("UserText", new Color(0.85f, 0.85f, 0.85f, 1f), 22,
            new Vector2(0f, 0.55f), new Vector2(1f, 1f));
        _avatarText = CreateLabel("AvatarText", Color.white, 26,
            new Vector2(0f, 0f), new Vector2(1f, 0.55f));
    }

    private Text CreateLabel(string name, Color color, int fontSize, Vector2 anchorMin, Vector2 anchorMax)
    {
        var go = new GameObject(name);
        go.transform.SetParent(transform, false);
        var rect = go.AddComponent<RectTransform>();
        rect.anchorMin = anchorMin;
        rect.anchorMax = anchorMax;
        rect.offsetMin = new Vector2(24f, 4f);
        rect.offsetMax = new Vector2(-24f, -4f);

        var text = go.AddComponent<Text>();
        text.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
        text.fontSize = fontSize;
        text.color = color;
        text.alignment = TextAnchor.MiddleCenter;
        text.horizontalOverflow = HorizontalWrapMode.Wrap;
        text.verticalOverflow = VerticalWrapMode.Truncate;
        text.text = "";
        return text;
    }

    private void OnEnable()
    {
        if (conversationClient != null)
        {
            conversationClient.OnStateChanged += HandleState;
            conversationClient.OnTranscript += HandleTranscript;
            conversationClient.OnSpeakSegmentStarted += HandleSpeakSegment;
        }
    }

    private void OnDisable()
    {
        if (conversationClient != null)
        {
            conversationClient.OnStateChanged -= HandleState;
            conversationClient.OnTranscript -= HandleTranscript;
            conversationClient.OnSpeakSegmentStarted -= HandleSpeakSegment;
        }
    }

    private void HandleState(string state)
    {
        _thinking = state == "thinking";
        _group.alpha = (state == "listening") ? 0f : 1f;

        if (state == "listening")
        {
            _userText.text = "";
            _avatarText.text = "";
        }
    }

    private void HandleTranscript(string text)
    {
        _userText.text = DisplayText(text);
    }

    private void HandleSpeakSegment(string text)
    {
        _avatarText.text = DisplayText(text);
    }

    private void Update()
    {
        if (!_thinking) return;
        int dots = 1 + Mathf.FloorToInt(Time.time * dotsSpeed) % 3;
        _avatarText.text = new string('.', dots);
    }

    /// <summary>
    /// Legacy uGUI Text renders characters left-to-right regardless of script.
    /// For predominantly-Hebrew strings, reverse the character order so the text
    /// reads correctly as a block; mixed he/en sentences may still look off — a
    /// proper fix needs TextMeshPro + an RTL shaping helper.
    /// </summary>
    private static string DisplayText(string text)
    {
        if (string.IsNullOrEmpty(text)) return text;

        int hebrewCount = 0;
        foreach (char c in text)
        {
            if (c >= (char)0x0590 && c <= (char)0x05FF) hebrewCount++;
        }
        if (hebrewCount * 2 < text.Length) return text; // not predominantly Hebrew

        var chars = text.ToCharArray();
        System.Array.Reverse(chars);
        return new string(chars);
    }
}
