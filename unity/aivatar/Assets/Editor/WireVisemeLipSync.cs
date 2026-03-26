using UnityEngine;
using UnityEditor;
using System.Text;

/// <summary>
/// Wires up the MetaHuman face (FaceMesh3) with baked viseme blendshapes for ProLipSync.
/// Aligns FaceMesh3 to the body, disables the old static face, and configures ProLipSync.
/// </summary>
public class WireVisemeLipSync
{
    public static string Run()
    {
        var sb = new StringBuilder();

        // Step 1: Find the body root and the static face MeshRenderer
        Transform bodyRoot = null;
        MeshRenderer staticFace = null;
        foreach (var go in UnityEngine.SceneManagement.SceneManager.GetActiveScene().GetRootGameObjects())
        {
            if (go.name == "SKM_model4_BodyMesh")
            {
                bodyRoot = go.transform;
                break;
            }
        }
        if (bodyRoot == null) return "ERROR: SKM_model4_BodyMesh not found in scene";

        // Find the static face MeshRenderer under the body
        foreach (var mr in bodyRoot.GetComponentsInChildren<MeshRenderer>())
        {
            if (mr.gameObject.name == "SKM_model4_FaceMesh")
            {
                staticFace = mr;
                break;
            }
        }
        if (staticFace == null)
            sb.AppendLine("WARNING: Static face MeshRenderer not found (already disabled?)");

        // Step 2: Find FaceMesh3 SkinnedMeshRenderer
        SkinnedMeshRenderer faceSMR = null;
        Transform faceMesh3Root = null;
        foreach (var go in UnityEngine.SceneManagement.SceneManager.GetActiveScene().GetRootGameObjects())
        {
            if (go.name == "SKM_model4_FaceMesh3")
            {
                faceMesh3Root = go.transform;
                foreach (var smr in go.GetComponentsInChildren<SkinnedMeshRenderer>())
                {
                    if (smr.bones.Length > 800)
                    {
                        faceSMR = smr;
                        break;
                    }
                }
                break;
            }
        }
        if (faceSMR == null) return "ERROR: FaceMesh3 SkinnedMeshRenderer not found";

        // Step 3: Check if mesh has blendshapes
        var mesh = faceSMR.sharedMesh;
        sb.AppendLine($"FaceMesh3 SMR mesh: {mesh.name}, blendShapes: {mesh.blendShapeCount}");
        if (mesh.blendShapeCount == 0)
        {
            sb.AppendLine("No blendshapes — need to run BakeVisemesFromBones first!");
            return sb.ToString();
        }

        // Step 4: Align FaceMesh3 to the body position
        // The body's face is at bodyRoot position, but the face bones in the body
        // are at a specific offset. We need to match FaceMesh3's root to bodyRoot.
        if (staticFace != null)
        {
            sb.AppendLine($"Body position: {bodyRoot.position}");
            sb.AppendLine($"FaceMesh3 position: {faceMesh3Root.position}");

            // Match the FaceMesh3 root transform to the body root
            faceMesh3Root.position = bodyRoot.position;
            faceMesh3Root.rotation = bodyRoot.rotation;
            faceMesh3Root.localScale = bodyRoot.localScale;
            sb.AppendLine($"Aligned FaceMesh3 to body at {bodyRoot.position}");

            // Disable the static face MeshRenderer
            staticFace.enabled = false;
            sb.AppendLine($"Disabled static face MeshRenderer");
            EditorUtility.SetDirty(staticFace);
        }

        // Step 5: Wire up ProLipSync on the Avatar (or create one)
        // Find existing AzureSpeechManager
        var speechMgr = Object.FindFirstObjectByType<AzureSpeechManager>();

        // Find or create ProLipSync on FaceMesh3
        var proLipSync = faceSMR.GetComponent<ProLipSync>();
        if (proLipSync == null)
            proLipSync = faceSMR.gameObject.AddComponent<ProLipSync>();

        proLipSync.faceMesh = faceSMR;

        // Find the VisemeMapping asset
        var mapping = AssetDatabase.LoadAssetAtPath<VisemeMapping>("Assets/Model4VisemeMapping.asset");
        if (mapping != null)
        {
            proLipSync.mappingProfile = mapping;
            sb.AppendLine("Wired VisemeMapping profile");
        }
        else
        {
            sb.AppendLine("WARNING: Model4VisemeMapping.asset not found");
        }

        // Wire speech manager to use this lip sync controller
        if (speechMgr != null)
        {
            speechMgr.lipSyncController = proLipSync;
            EditorUtility.SetDirty(speechMgr);
            sb.AppendLine($"Wired AzureSpeechManager.lipSyncController -> ProLipSync on {faceSMR.gameObject.name}");
        }
        else
        {
            sb.AppendLine("WARNING: AzureSpeechManager not found in scene");
        }

        // Ensure AudioSource exists
        var audioSource = faceSMR.GetComponent<AudioSource>();
        if (audioSource == null)
        {
            audioSource = faceSMR.gameObject.AddComponent<AudioSource>();
            sb.AppendLine("Added AudioSource component");
        }

        EditorUtility.SetDirty(proLipSync);
        EditorUtility.SetDirty(faceSMR.gameObject);
        EditorUtility.SetDirty(faceMesh3Root.gameObject);

        // Also disable other face-related objects that might overlap
        // (SKM_model4_FaceMesh_Visemes, SKM_model4_FaceMesh root)
        foreach (var go in UnityEngine.SceneManagement.SceneManager.GetActiveScene().GetRootGameObjects())
        {
            if (go.name == "SKM_model4_FaceMesh_Visemes")
            {
                go.SetActive(false);
                sb.AppendLine("Disabled SKM_model4_FaceMesh_Visemes");
            }
            if (go.name == "SKM_model4_FaceMesh" && go != faceMesh3Root?.gameObject)
            {
                go.SetActive(false);
                sb.AppendLine("Disabled standalone SKM_model4_FaceMesh");
            }
        }

        // List blendshapes for verification
        sb.AppendLine($"\nBlendshapes on mesh ({mesh.blendShapeCount}):");
        for (int i = 0; i < mesh.blendShapeCount; i++)
            sb.AppendLine($"  [{i}] {mesh.GetBlendShapeName(i)}");

        sb.AppendLine("\nSetup complete! Test with Play mode.");
        return sb.ToString();
    }
}
