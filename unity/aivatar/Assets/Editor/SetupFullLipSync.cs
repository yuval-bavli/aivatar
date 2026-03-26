using UnityEngine;
using UnityEditor;

public class SetupFullLipSync
{
    public static string Run()
    {
        var sb = new System.Text.StringBuilder();

        // Find FaceMesh3 SMR
        SkinnedMeshRenderer faceSMR = null;
        GameObject faceMesh3Root = null;
        foreach (var go in UnityEngine.SceneManagement.SceneManager.GetActiveScene().GetRootGameObjects())
        {
            if (go.name == "SKM_model4_FaceMesh3")
            {
                faceMesh3Root = go;
                foreach (var smr in go.GetComponentsInChildren<SkinnedMeshRenderer>())
                {
                    if (smr.bones.Length > 800) { faceSMR = smr; break; }
                }
            }
        }
        if (faceSMR == null) return "ERROR: FaceMesh3 SMR not found";

        // Restore original FBX mesh
        var fbxMesh = AssetDatabase.LoadAssetAtPath<Mesh>("Assets/Models/Avatar/SKM_model4_FaceMesh3.FBX");
        if (fbxMesh != null)
        {
            faceSMR.sharedMesh = fbxMesh;
            sb.AppendLine("Restored original FBX mesh");
        }

        // Fix materials
        sb.AppendLine(FixMaterials.ApplyCorrect());

        // DESTROY old lip sync components (not just disable)
        var proLipSync = faceSMR.GetComponent<ProLipSync>();
        if (proLipSync != null) { Object.DestroyImmediate(proLipSync); sb.AppendLine("Removed ProLipSync"); }
        var playModeTest = faceSMR.GetComponent<TestVisemePlayMode>();
        if (playModeTest != null) { Object.DestroyImmediate(playModeTest); sb.AppendLine("Removed TestVisemePlayMode"); }
        // Also remove any BoneLipSync or MeshLipSync
        var boneLipSync = faceSMR.GetComponent<BoneLipSync>();
        if (boneLipSync != null) { Object.DestroyImmediate(boneLipSync); sb.AppendLine("Removed BoneLipSync"); }

        // Add MetaHumanLipSync
        var mhLipSync = faceSMR.GetComponent<MetaHumanLipSync>();
        if (mhLipSync == null)
            mhLipSync = faceSMR.gameObject.AddComponent<MetaHumanLipSync>();
        mhLipSync.faceMesh = faceSMR;
        mhLipSync.enabled = true;
        EditorUtility.SetDirty(mhLipSync);
        sb.AppendLine("MetaHumanLipSync wired");

        // Ensure AudioSource
        if (faceSMR.GetComponent<AudioSource>() == null)
            faceSMR.gameObject.AddComponent<AudioSource>();

        // AzureSpeechManager — make sure it points to MetaHumanLipSync
        var speechMgr = faceSMR.GetComponent<AzureSpeechManager>();
        if (speechMgr == null)
            speechMgr = Object.FindFirstObjectByType<AzureSpeechManager>();
        if (speechMgr == null)
            speechMgr = faceSMR.gameObject.AddComponent<AzureSpeechManager>();
        speechMgr.lipSyncController = mhLipSync;
        EditorUtility.SetDirty(speechMgr);
        sb.AppendLine($"AzureSpeechManager.lipSyncController = MetaHumanLipSync (type: {speechMgr.lipSyncController.GetType().Name})");

        // TestSpeak
        var testSpeak = faceSMR.GetComponent<TestSpeak>();
        if (testSpeak == null)
            testSpeak = Object.FindFirstObjectByType<TestSpeak>();
        if (testSpeak == null)
            testSpeak = faceSMR.gameObject.AddComponent<TestSpeak>();
        testSpeak.speechManager = speechMgr;
        EditorUtility.SetDirty(testSpeak);

        // Also check for any OTHER ProLipSync in scene and remove
        foreach (var pl in Object.FindObjectsByType<ProLipSync>(FindObjectsSortMode.None))
        {
            Object.DestroyImmediate(pl);
            sb.AppendLine("Removed extra ProLipSync from scene");
        }

        UnityEditor.SceneManagement.EditorSceneManager.SaveOpenScenes();
        sb.AppendLine("\nScene saved. Press Play!");
        return sb.ToString();
    }
}
