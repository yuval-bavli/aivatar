using UnityEngine;
using UnityEditor;

public static class CreateTestEyebrows3
{
    [MenuItem("Aivatar/Create Test Eyebrows3")]
    public static string Run()
    {
        var log = new System.Text.StringBuilder();

        // Clean up ALL test objects
        foreach (var name in new[] { "TEST_EYEBROW_LEFT", "TEST_EYEBROW_RIGHT", "DEBUG_BROW_CUBE", "BIG_RED_TEST" })
        {
            var old = GameObject.Find(name);
            while (old != null) { Object.DestroyImmediate(old); old = GameObject.Find(name); }
        }

        var cam = Camera.main;
        if (cam == null) return "ERROR: no camera";

        log.AppendLine($"Camera: pos={cam.transform.position}, fwd={cam.transform.forward}");
        log.AppendLine($"Camera: near={cam.nearClipPlane}, far={cam.farClipPlane}");

        // Place a BIG red cube right in front of camera
        // Camera is at Z=-9.09, looking +Z. Place cube at Z=-8.5 (0.59 units in front)
        var cube = GameObject.CreatePrimitive(PrimitiveType.Cube);
        cube.name = "BIG_RED_TEST";
        cube.transform.position = cam.transform.position + cam.transform.forward * 0.5f;
        cube.transform.localScale = new Vector3(0.3f, 0.3f, 0.01f);

        var unlitShader = Shader.Find("Universal Render Pipeline/Unlit");
        if (unlitShader != null)
        {
            var mat = new Material(unlitShader);
            mat.SetColor("_BaseColor", Color.red);
            cube.GetComponent<Renderer>().material = mat;
        }
        else
        {
            cube.GetComponent<Renderer>().material.color = Color.red;
        }

        log.AppendLine($"Test cube at: {cube.transform.position}");
        log.AppendLine($"Distance from camera: {Vector3.Distance(cam.transform.position, cube.transform.position)}");

        // Also log all scene renderers with their bounds
        var renderers = Object.FindObjectsOfType<Renderer>();
        log.AppendLine($"\nAll renderers ({renderers.Length}):");
        foreach (var r in renderers)
        {
            float dist = Vector3.Distance(cam.transform.position, r.bounds.center);
            log.AppendLine($"  {r.gameObject.name}: center={r.bounds.center}, dist={dist:F3}, enabled={r.enabled}");
        }

        return log.ToString();
    }
}
