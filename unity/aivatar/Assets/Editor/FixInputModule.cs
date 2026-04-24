#if UNITY_EDITOR
using UnityEditor;
using UnityEngine;
using UnityEngine.EventSystems;

public static class FixInputModule
{
    public static string Run()
    {
        var es = Object.FindFirstObjectByType<EventSystem>();
        if (es == null) return "No EventSystem found";

        var old = es.GetComponent<StandaloneInputModule>();
        if (old != null)
        {
            Object.DestroyImmediate(old);
        }

        // Add InputSystemUIInputModule if available
        var existing = es.GetComponent("UnityEngine.InputSystem.UI.InputSystemUIInputModule");
        if (existing == null)
        {
            // Try to add it via type lookup
            foreach (var asm in System.AppDomain.CurrentDomain.GetAssemblies())
            {
                var t = asm.GetType("UnityEngine.InputSystem.UI.InputSystemUIInputModule");
                if (t != null)
                {
                    es.gameObject.AddComponent(t);
                    EditorUtility.SetDirty(es.gameObject);
                    return "Replaced StandaloneInputModule with InputSystemUIInputModule";
                }
            }
            return "Removed StandaloneInputModule but InputSystemUIInputModule type not found";
        }

        return "StandaloneInputModule removed, InputSystemUIInputModule already present";
    }
}
#endif
