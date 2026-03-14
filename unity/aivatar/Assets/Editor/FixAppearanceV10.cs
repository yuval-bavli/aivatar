using UnityEngine;
using UnityEditor;

public static class FixAppearanceV10
{
    [MenuItem("Aivatar/Fix Appearance V10")]
    public static string Run()
    {
        var log = new System.Text.StringBuilder();

        // Clean up previous debug cube
        var oldCube = GameObject.Find("DEBUG_BROW_CUBE");
        if (oldCube != null) Object.DestroyImmediate(oldCube);

        // Find camera and log its position
        var cam = Camera.main;
        if (cam != null)
        {
            log.AppendLine($"Camera pos: {cam.transform.position}");
            log.AppendLine($"Camera rot: {cam.transform.eulerAngles}");
            log.AppendLine($"Camera fov: {cam.fieldOfView}");
            log.AppendLine($"Camera near/far: {cam.nearClipPlane}/{cam.farClipPlane}");
        }
        else
        {
            log.AppendLine("No main camera found!");
            // Check scene view camera
            var sceneView = UnityEditor.SceneView.lastActiveSceneView;
            if (sceneView != null)
            {
                log.AppendLine($"SceneView camera pivot: {sceneView.pivot}");
                log.AppendLine($"SceneView camera pos: {sceneView.camera.transform.position}");
                log.AppendLine($"SceneView camera rot: {sceneView.camera.transform.eulerAngles}");
            }
        }

        // Log all cameras
        var cameras = Object.FindObjectsOfType<Camera>();
        log.AppendLine($"\nAll cameras ({cameras.Length}):");
        foreach (var c in cameras)
        {
            log.AppendLine($"  {c.gameObject.name}: pos={c.transform.position}, rot={c.transform.eulerAngles}, " +
                           $"tag={c.gameObject.tag}, depth={c.depth}, enabled={c.enabled}, " +
                           $"cullingMask={c.cullingMask}");
        }

        // Log key renderers world positions for reference
        var renderers = Object.FindObjectsOfType<Renderer>();
        log.AppendLine($"\nRenderer positions:");
        foreach (var r in renderers)
        {
            log.AppendLine($"  {r.gameObject.name}: center={r.bounds.center}, size={r.bounds.size}");
        }

        // Create a BIG debug cube at a known visible position (center of face area)
        var faceMesh = FindByName("SKM_model4_FaceMesh");
        if (faceMesh != null)
        {
            var faceRenderer = faceMesh.GetComponent<Renderer>();
            if (faceRenderer != null)
            {
                // Place cube at the face center, slightly forward
                Vector3 cubePos = faceRenderer.bounds.center;
                cubePos.z -= 0.2f; // Push towards camera
                var cube = GameObject.CreatePrimitive(PrimitiveType.Cube);
                cube.name = "DEBUG_BROW_CUBE";
                cube.transform.position = cubePos;
                cube.transform.localScale = new Vector3(0.1f, 0.02f, 0.02f);
                var cubeRenderer = cube.GetComponent<Renderer>();
                cubeRenderer.material = new Material(Shader.Find("Universal Render Pipeline/Unlit"));
                cubeRenderer.material.color = Color.red;
                log.AppendLine($"\nDebug cube at: {cube.transform.position} (in front of face center)");
            }
        }

        string result = log.ToString();
        Debug.Log(result);
        return result;
    }

    static GameObject FindByName(string name)
    {
        foreach (var go in Object.FindObjectsOfType<GameObject>())
        {
            if (go.name == name) return go;
        }
        return null;
    }
}
