using UnityEngine;
using UnityEditor;

public static class CreateTestEyebrows2
{
    [MenuItem("Aivatar/Create Test Eyebrows2")]
    public static string Run()
    {
        var log = new System.Text.StringBuilder();

        // Clean up
        foreach (var name in new[] { "TEST_EYEBROW_LEFT", "TEST_EYEBROW_RIGHT", "DEBUG_BROW_CUBE" })
        {
            var old = GameObject.Find(name);
            if (old != null) Object.DestroyImmediate(old);
        }

        // Face reference
        Renderer faceRenderer = null;
        foreach (var r in Object.FindObjectsOfType<Renderer>())
            if (r.gameObject.name == "SKM_model4_FaceMesh") { faceRenderer = r; break; }
        if (faceRenderer == null) return "ERROR: face not found";

        var fc = faceRenderer.bounds.center;
        var fs = faceRenderer.bounds.size;

        // Eyebrow position: above eye level, in front of face
        float browY = fc.y + fs.y * 0.15f;
        float browZ = fc.z - fs.z * 0.50f; // Further in front to be visible

        // Create quads facing the camera (rotated 180 around Y)
        var leftBrow = GameObject.CreatePrimitive(PrimitiveType.Quad);
        leftBrow.name = "TEST_EYEBROW_LEFT";
        leftBrow.transform.position = new Vector3(fc.x - 0.04f, browY, browZ);
        leftBrow.transform.localScale = new Vector3(0.06f, 0.015f, 1f);
        leftBrow.transform.rotation = Quaternion.Euler(0, 180, 0); // Face camera

        var rightBrow = GameObject.CreatePrimitive(PrimitiveType.Quad);
        rightBrow.name = "TEST_EYEBROW_RIGHT";
        rightBrow.transform.position = new Vector3(fc.x + 0.04f, browY, browZ);
        rightBrow.transform.localScale = new Vector3(0.06f, 0.015f, 1f);
        rightBrow.transform.rotation = Quaternion.Euler(0, 180, 0); // Face camera

        // Bright red unlit material
        var unlitShader = Shader.Find("Universal Render Pipeline/Unlit");
        foreach (var go in new[] { leftBrow, rightBrow })
        {
            var r = go.GetComponent<Renderer>();
            var mat = new Material(unlitShader);
            mat.SetColor("_BaseColor", Color.red);
            r.material = mat;
            log.AppendLine($"{go.name}: pos={go.transform.position}");
        }

        log.AppendLine($"Face: center={fc}, frontZ={fc.z - fs.z * 0.5f}");

        AssetDatabase.SaveAssets();
        string result = log.ToString();
        Debug.Log(result);
        return result;
    }
}
