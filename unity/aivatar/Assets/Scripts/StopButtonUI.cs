using UnityEngine;
using UnityEngine.UI;

/// <summary>
/// Wires a uGUI Button to ConversationClient.Stop().
/// Attach to the same GameObject as a Button component.
/// </summary>
[RequireComponent(typeof(Button))]
public class StopButtonUI : MonoBehaviour
{
    public ConversationClient conversationClient;

    private void Start()
    {
        GetComponent<Button>().onClick.AddListener(() => conversationClient?.Stop());
    }
}
