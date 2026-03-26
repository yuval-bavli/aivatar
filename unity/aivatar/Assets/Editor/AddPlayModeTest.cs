using UnityEngine;
using UnityEditor;

public class AddPlayModeTest
{
    public static string Run()
    {
        foreach (var go in UnityEngine.SceneManagement.SceneManager.GetActiveScene().GetRootGameObjects())
        {
            if (go.name == "SKM_model4_FaceMesh3")
            {
                var smr = go.GetComponentInChildren<SkinnedMeshRenderer>();
                if (smr == null) return "ERROR: No SMR on FaceMesh3";

                var test = smr.GetComponent<TestVisemePlayMode>();
                if (test == null)
                    test = smr.gameObject.AddComponent<TestVisemePlayMode>();

                test.faceMesh = smr;
                test.autoCycle = true;
                test.cycleSpeed = 1.5f;

                EditorUtility.SetDirty(test);
                EditorUtility.SetDirty(smr.gameObject);

                // Save scene
                UnityEditor.SceneManagement.EditorSceneManager.SaveOpenScenes();

                return $"Added TestVisemePlayMode to {smr.gameObject.name}. Enter Play mode to test. Scene saved.";
            }
        }
        return "ERROR: SKM_model4_FaceMesh3 not found";
    }
}
