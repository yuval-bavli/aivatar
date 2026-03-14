using UnityEngine;
using UnityEditor;

public static class FixAppearanceV9
{
    [MenuItem("Aivatar/Fix Appearance V9")]
    public static string Run()
    {
        var log = new System.Text.StringBuilder();

        var browGO = FindByName("Eyebrows_M_Natural_CardsMesh_Group0_LOD0");
        if (browGO == null)
        {
            log.AppendLine("ERROR: Eyebrow mesh not found");
            return log.ToString();
        }

        // Reset position
        browGO.transform.localPosition = new Vector3(0.04f, 0f, 0.04f);

        // Check layer
        log.AppendLine($"Eyebrow layer: {browGO.layer} ({LayerMask.LayerToName(browGO.layer)})");

        // Check camera culling mask
        var cam = Camera.main;
        if (cam != null)
        {
            log.AppendLine($"Camera culling mask: {cam.cullingMask}");
            bool layerVisible = (cam.cullingMask & (1 << browGO.layer)) != 0;
            log.AppendLine($"Eyebrow layer visible to camera: {layerVisible}");
        }

        // Check renderer
        var renderer = browGO.GetComponent<MeshRenderer>();
        if (renderer != null)
        {
            log.AppendLine($"Renderer.enabled: {renderer.enabled}");
            log.AppendLine($"Renderer.isVisible: {renderer.isVisible}");
            log.AppendLine($"Renderer.sortingOrder: {renderer.sortingOrder}");
            log.AppendLine($"Renderer.sortingLayerName: {renderer.sortingLayerName}");
            log.AppendLine($"Renderer.receiveShadows: {renderer.receiveShadows}");
            log.AppendLine($"Renderer.shadowCastingMode: {renderer.shadowCastingMode}");
            log.AppendLine($"Renderer.lightProbeUsage: {renderer.lightProbeUsage}");
            log.AppendLine($"Renderer.forceRenderingOff: {renderer.forceRenderingOff}");
        }

        // Check mesh filter
        var mf = browGO.GetComponent<MeshFilter>();
        if (mf != null)
        {
            var mesh = mf.sharedMesh;
            if (mesh != null)
            {
                log.AppendLine($"Mesh.isReadable: {mesh.isReadable}");
                log.AppendLine($"Mesh.vertexCount: {mesh.vertexCount}");
                log.AppendLine($"Mesh.subMeshCount: {mesh.subMeshCount}");
                for (int i = 0; i < mesh.subMeshCount; i++)
                {
                    var desc = mesh.GetSubMesh(i);
                    log.AppendLine($"  SubMesh[{i}]: topology={desc.topology}, indexCount={desc.indexCount}, vertexCount={desc.vertexCount}");
                }

                // Check if vertices are valid (not all zero)
                var verts = mesh.vertices;
                int zeroVerts = 0;
                Vector3 vMin = verts[0], vMax = verts[0];
                for (int i = 0; i < verts.Length; i++)
                {
                    if (verts[i] == Vector3.zero) zeroVerts++;
                    vMin = Vector3.Min(vMin, verts[i]);
                    vMax = Vector3.Max(vMax, verts[i]);
                }
                log.AppendLine($"Vertex range: min={vMin}, max={vMax}");
                log.AppendLine($"Zero vertices: {zeroVerts}/{verts.Length}");
            }
        }

        // Check all parent game objects are active
        var t = browGO.transform;
        while (t != null)
        {
            log.AppendLine($"  {t.name}: activeSelf={t.gameObject.activeSelf}, layer={t.gameObject.layer}");
            t = t.parent;
        }

        // Create a test cube at the eyebrow position to verify camera can see it
        var cube = GameObject.CreatePrimitive(PrimitiveType.Cube);
        cube.name = "DEBUG_BROW_CUBE";
        cube.transform.position = browGO.GetComponent<Renderer>().bounds.center;
        cube.transform.localScale = new Vector3(0.05f, 0.05f, 0.05f);
        var cubeRenderer = cube.GetComponent<Renderer>();
        cubeRenderer.material.color = Color.red;
        log.AppendLine($"\nCreated debug cube at: {cube.transform.position}");

        EditorUtility.SetDirty(browGO);
        AssetDatabase.SaveAssets();
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
