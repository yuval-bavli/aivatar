using UnityEngine;
using UnityEditor;
using System.Text;

public class SceneCheck
{
    public static string Run()
    {
        var sb = new StringBuilder();

        // List ALL renderers in scene
        sb.AppendLine("=== All Renderers ===");
        foreach (var r in Object.FindObjectsByType<Renderer>(FindObjectsSortMode.None))
        {
            string path = GetPath(r.transform);
            sb.AppendLine($"  {r.GetType().Name}: {path} | enabled={r.enabled} active={r.gameObject.activeInHierarchy} pos={r.transform.position}");
        }

        // List all root GameObjects
        sb.AppendLine("=== Root GameObjects ===");
        var scene = UnityEngine.SceneManagement.SceneManager.GetActiveScene();
        foreach (var go in scene.GetRootGameObjects())
        {
            sb.AppendLine($"  {go.name} active={go.activeSelf}");
            // List immediate children
            for (int i = 0; i < go.transform.childCount; i++)
            {
                var child = go.transform.GetChild(i);
                sb.AppendLine($"    {child.name} active={child.gameObject.activeSelf}");
            }
        }

        // Camera info
        sb.AppendLine("=== Cameras ===");
        foreach (var cam in Object.FindObjectsByType<Camera>(FindObjectsSortMode.None))
        {
            sb.AppendLine($"  {cam.name}: pos={cam.transform.position} fwd={cam.transform.forward} fov={cam.fieldOfView}");
        }

        return sb.ToString();
    }

    static string GetPath(Transform t)
    {
        var sb = new StringBuilder(t.name);
        var p = t.parent;
        while (p != null)
        {
            sb.Insert(0, p.name + "/");
            p = p.parent;
        }
        return sb.ToString();
    }
}
