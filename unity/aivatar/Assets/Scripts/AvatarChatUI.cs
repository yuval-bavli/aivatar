using UnityEngine;
using UnityEngine.UI;
using TMPro;

public class AvatarChatUI : MonoBehaviour
{
    [Header("References")]
    public AzureSpeechManager speechManager;
    public TMP_InputField inputField;
    public Button sendButton;

    void Start()
    {
        sendButton.onClick.AddListener(Submit);
        inputField.onSubmit.AddListener(_ => Submit());
        inputField.ActivateInputField();
    }

    void Submit()
    {
        string text = inputField.text.Trim();
        if (string.IsNullOrEmpty(text)) return;

        speechManager.Speak(text);
        inputField.text = "";
        inputField.ActivateInputField();
    }
}
