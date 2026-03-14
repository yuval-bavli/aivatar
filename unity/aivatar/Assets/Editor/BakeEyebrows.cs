using UnityEngine;
using UnityEditor;
using System.IO;
using System.Collections.Generic;

public static class BakeEyebrows
{
    [MenuItem("Aivatar/Bake Eyebrows")]
    public static string Run()
    {
        var log = new System.Text.StringBuilder();

        // Find the face mesh renderer
        Renderer faceRenderer = null;
        MeshFilter faceMF = null;
        foreach (var r in Object.FindObjectsOfType<Renderer>())
        {
            if (r.gameObject.name == "SKM_model4_FaceMesh" && r is MeshRenderer)
            {
                faceRenderer = r;
                faceMF = r.GetComponent<MeshFilter>();
                break;
            }
        }

        if (faceRenderer == null || faceMF == null || faceMF.sharedMesh == null)
            return "ERROR: face mesh not found";

        var mesh = faceMF.sharedMesh;
        log.AppendLine($"Face mesh: {mesh.vertexCount} verts, {mesh.subMeshCount} submeshes");

        // Get submesh 0 (face skin) vertices and UVs
        var vertices = mesh.vertices;
        var uvs = mesh.uv;
        var normals = mesh.normals;
        var triangles = mesh.GetTriangles(0); // Submesh 0 = face skin

        // Transform vertices to world space
        var transform = faceRenderer.transform;

        // Find the eyebrow area: vertices that are in the upper face region
        // Face center Y ≈ 1.49, eyebrow area ≈ Y 1.54-1.60 in world space
        // Also should be on the front of the face (Z close to front)

        float browMinY = 1.54f;
        float browMaxY = 1.62f;
        float browMinZ = -8.80f; // Front of face
        float browMaxZ = -8.68f;

        List<Vector2> browUVs = new List<Vector2>();
        List<int> browVertIndices = new List<int>();

        // Collect UVs from face skin submesh vertices in the eyebrow region
        HashSet<int> submesh0Verts = new HashSet<int>();
        foreach (int idx in triangles)
            submesh0Verts.Add(idx);

        for (int i = 0; i < vertices.Length; i++)
        {
            if (!submesh0Verts.Contains(i)) continue;

            Vector3 worldPos = transform.TransformPoint(vertices[i]);
            if (worldPos.y >= browMinY && worldPos.y <= browMaxY &&
                worldPos.z >= browMinZ && worldPos.z <= browMaxZ)
            {
                browUVs.Add(uvs[i]);
                browVertIndices.Add(i);
            }
        }

        log.AppendLine($"Found {browUVs.Count} vertices in eyebrow region");

        if (browUVs.Count > 0)
        {
            Vector2 uvMin = browUVs[0], uvMax = browUVs[0];
            foreach (var uv in browUVs)
            {
                uvMin = Vector2.Min(uvMin, uv);
                uvMax = Vector2.Max(uvMax, uv);
            }
            log.AppendLine($"Eyebrow UV range: min={uvMin}, max={uvMax}");

            // Sample a few specific vertices
            for (int i = 0; i < Mathf.Min(10, browUVs.Count); i++)
            {
                Vector3 wp = transform.TransformPoint(vertices[browVertIndices[i]]);
                log.AppendLine($"  vert[{browVertIndices[i]}]: world={wp}, uv={browUVs[i]}");
            }
        }

        // Also check what the face texture looks like - load it
        var faceSkinMat = AssetDatabase.LoadAssetAtPath<Material>(
            "Assets/Models/Avatar/Materials/MI_Face_Skin_Baked_LOD1_VT.mat");
        if (faceSkinMat != null)
        {
            var faceTex = faceSkinMat.GetTexture("_BaseMap") as Texture2D;
            if (faceTex != null)
            {
                log.AppendLine($"\nFace texture: {faceTex.name} ({faceTex.width}x{faceTex.height})");

                // Check importer settings
                string texPath = AssetDatabase.GetAssetPath(faceTex);
                log.AppendLine($"Texture path: {texPath}");
                var importer = AssetImporter.GetAtPath(texPath) as TextureImporter;
                if (importer != null)
                {
                    log.AppendLine($"Readable: {importer.isReadable}");
                    // Make readable if needed
                    if (!importer.isReadable)
                    {
                        importer.isReadable = true;
                        importer.SaveAndReimport();
                        log.AppendLine("Made texture readable");
                    }
                }
            }
        }

        string result = log.ToString();
        string path = Path.Combine(Application.dataPath, "..", "bake_eyebrows_log.txt");
        File.WriteAllText(path, result);
        Debug.Log(result);
        return result;
    }
}
