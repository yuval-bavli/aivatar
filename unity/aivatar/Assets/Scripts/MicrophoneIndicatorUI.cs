using UnityEngine;
using UnityEngine.UI;

[RequireComponent(typeof(CanvasGroup))]
public class MicrophoneIndicatorUI : MonoBehaviour
{
    public ConversationClient conversationClient;
    public Texture2D          micTexture;

    [Range(0f, 1f)] public float minAlpha    = 0.35f;
    public float                 pulseSpeed  = 1.5f;
    [Range(0, 50)]  public int   cornerRadius = 15;

    private CanvasGroup _group;
    private bool        _listening;

    private void Awake()
    {
        _group       = GetComponent<CanvasGroup>();
        _group.alpha = 0f;
        BuildUI();
    }

    private void BuildUI()
    {
        // Rounded-rect mask
        var maskGO   = new GameObject("Mask");
        maskGO.transform.SetParent(transform, false);
        var maskRect = maskGO.AddComponent<RectTransform>();
        maskRect.anchorMin = Vector2.zero;
        maskRect.anchorMax = Vector2.one;
        maskRect.offsetMin = maskRect.offsetMax = Vector2.zero;
        var maskImg  = maskGO.AddComponent<Image>();
        maskImg.sprite = CreateRoundedRectSprite(128, cornerRadius * 128 / 80);
        maskGO.AddComponent<Mask>().showMaskGraphic = false;

        // Microphone texture inside mask
        var iconGO   = new GameObject("Icon");
        iconGO.transform.SetParent(maskGO.transform, false);
        var iconRect = iconGO.AddComponent<RectTransform>();
        iconRect.anchorMin = Vector2.zero;
        iconRect.anchorMax = Vector2.one;
        iconRect.offsetMin = iconRect.offsetMax = Vector2.zero;
        var raw      = iconGO.AddComponent<RawImage>();
        raw.texture  = micTexture;
    }

    private static Sprite CreateRoundedRectSprite(int size, int radius)
    {
        var tex    = new Texture2D(size, size, TextureFormat.RGBA32, false);
        var pixels = new Color32[size * size];
        float half  = size * 0.5f;
        float inner = half - radius;

        for (int y = 0; y < size; y++)
        {
            for (int x = 0; x < size; x++)
            {
                float dx   = Mathf.Max(0f, Mathf.Abs(x - half + 0.5f) - inner);
                float dy   = Mathf.Max(0f, Mathf.Abs(y - half + 0.5f) - inner);
                float dist = Mathf.Sqrt(dx * dx + dy * dy);
                byte  a    = (byte)(Mathf.Clamp01(radius - dist + 0.5f) * 255f);
                pixels[y * size + x] = new Color32(255, 255, 255, a);
            }
        }

        tex.SetPixels32(pixels);
        tex.Apply();
        return Sprite.Create(tex, new Rect(0, 0, size, size), new Vector2(0.5f, 0.5f));
    }

    private void OnEnable()
    {
        if (conversationClient != null)
            conversationClient.OnStateChanged += HandleState;
    }

    private void OnDisable()
    {
        if (conversationClient != null)
            conversationClient.OnStateChanged -= HandleState;
    }

    private void HandleState(string state)
    {
        _listening = state == "listening";
        if (!_listening) _group.alpha = 0f;
    }

    private void Update()
    {
        if (!_listening) return;
        float t      = Mathf.PingPong(Time.time * pulseSpeed, 1f);
        _group.alpha = Mathf.Lerp(minAlpha, 1f, t);
    }
}
