using UnityEngine;
using UnityEditor;
using System.Collections.Generic;

public class VisemeExtractor
{
    public static string Run()
    {
        int deletedCount = 0;
        // Find and delete the incorrectly placed GameObject in the active scene
        // Need to use Resources.FindObjectsOfTypeAll or similar if it's inactive,
        // but FindObjectsOfType usually finds active ones in scene.
        foreach (GameObject go in Object.FindObjectsByType<GameObject>(FindObjectsSortMode.None))
        {
            if (go.name.Contains("viseme_animation"))
            {
                Object.DestroyImmediate(go);
                deletedCount++;
            }
        }

        string fbxPath = "Assets/Models/Avatar/viseme_animation.fbx";
        ModelImporter importer = AssetImporter.GetAtPath(fbxPath) as ModelImporter;
        if (importer == null)
        {
            return "ERROR: Could not find ModelImporter for " + fbxPath;
        }

        // The sequence has frames 0, 10, 20... 140
        string[] visemes = { "sil", "PP", "FF", "TH", "DD", "kk", "CH", "SS", "nn", "RR", "aa", "E", "ih", "oh", "ou" };
        List<ModelImporterClipAnimation> clips = new List<ModelImporterClipAnimation>();

        for (int i = 0; i < visemes.Length; i++)
        {
            ModelImporterClipAnimation clip = new ModelImporterClipAnimation();
            clip.name = visemes[i];
            
            // For a single pose, typically we can capture a very short range, e.g. frame i*10 to i*10 + 1
            clip.firstFrame = i * 10;
            clip.lastFrame = i * 10 + 1;
            clip.loopTime = true; // Make it loopable so the state machine can hold it easily
            
            clips.Add(clip);
        }

        importer.clipAnimations = clips.ToArray();
        importer.SaveAndReimport();

        return "OK - Deleted " + deletedCount + " objects from scene and split FBX into 15 viseme clips.";
    }
}
