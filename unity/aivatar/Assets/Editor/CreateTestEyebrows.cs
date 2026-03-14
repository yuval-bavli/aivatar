using UnityEngine;
using UnityEditor;

public static class CreateTestEyebrows
{
    [MenuItem("Aivatar/Create Test Eyebrows")]
    public static string Run()
    {
        var log = new System.Text.StringBuilder();

        // Clean up any previous test objects
        var old = GameObject.Find("TEST_EYEBROW_LEFT");
        if (old != null) Object.DestroyImmediate(old);
        old = GameObject.Find("TEST_EYEBROW_RIGHT");
        if (old != null) Object.DestroyImmediate(old);

        // Find face mesh for reference position
        Renderer faceRenderer = null;
        foreach (var r in Object.FindObjectsOfType<Renderer>())
        {
            if (r.gameObject.name == "SKM_model4_FaceMesh")
            {
                faceRenderer = r;
                break;
            }
        }

        if (faceRenderer == null) return "ERROR: face not found";

        var faceCenter = faceRenderer.bounds.center;
        var faceSize = faceRenderer.bounds.size;
        log.AppendLine($"Face center: {faceCenter}, size: {faceSize}");

        // Camera info
        var cam = Camera.main;
        if (cam != null)
        {
            log.AppendLine($"Camera: pos={cam.transform.position}, near={cam.nearClipPlane}");
            float distToFace = Vector3.Distance(cam.transform.position, faceCenter);
            log.AppendLine($"Distance to face: {distToFace}");
        }

        // Create simple quad eyebrows at correct face position
        // Face top (forehead) is at center.y + extents.y
        float eyebrowY = faceCenter.y + faceSize.y * 0.15f; // Slightly above center
        float eyebrowZ = faceCenter.z - faceSize.z * 0.45f; // Just in front of face

        log.AppendLine($"Eyebrow target Y: {eyebrowY}, Z: {eyebrowZ}");

        // Load hair texture for eyebrow material
        var hairTex = AssetDatabase.LoadAssetAtPath<Texture2D>(
            "Assets/Models/Avatar/Textures/HairCard0_Color_1K.png");

        // Create left eyebrow quad
        var leftBrow = CreateQuad("TEST_EYEBROW_LEFT",
            new Vector3(faceCenter.x - 0.04f, eyebrowY, eyebrowZ),
            new Vector3(0.06f, 0.01f, 0.001f));

        // Create right eyebrow quad
        var rightBrow = CreateQuad("TEST_EYEBROW_RIGHT",
            new Vector3(faceCenter.x + 0.04f, eyebrowY, eyebrowZ),
            new Vector3(0.06f, 0.01f, 0.001f));

        // Apply red material to test visibility
        var unlitShader = Shader.Find("Universal Render Pipeline/Unlit");
        log.AppendLine($"Unlit shader found: {unlitShader != null}");

        foreach (var go in new[] { leftBrow, rightBrow })
        {
            var r = go.GetComponent<Renderer>();
            if (unlitShader != null)
            {
                r.material = new Material(unlitShader);
                r.material.color = Color.red;
            }
            else
            {
                r.material.color = Color.red;
            }
            log.AppendLine($"{go.name}: pos={go.transform.position}, bounds={r.bounds.center}");
        }

        // Also: disable the original eyebrow mesh to avoid confusion
        foreach (var r in Object.FindObjectsOfType<Renderer>())
        {
            if (r.gameObject.name == "Eyebrows_M_Natural_CardsMesh_Group0_LOD0")
            {
                r.enabled = false;
                log.AppendLine("Disabled original eyebrow mesh");
            }
        }

        AssetDatabase.SaveAssets();
        string result = log.ToString();
        Debug.Log(result);
        return result;
    }

    static GameObject CreateQuad(string name, Vector3 position, Vector3 scale)
    {
        var go = GameObject.CreatePrimitive(PrimitiveType.Quad);
        go.name = name;
        go.transform.position = position;
        go.transform.localScale = scale;
        // Face the quad towards the camera (-Z direction)
        go.transform.rotation = Quaternion.identity;
        return go;
    }
}
