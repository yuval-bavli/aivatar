using UnityEngine;
using System.IO;

public class MetaHumanEyeBaker : MonoBehaviour
{
    public Texture2D scleraTexture;
    public Texture2D irisTexture;
    public string saveName = "BakedEyeRight";

    [ContextMenu("Bake Eye Texture")]
    public void Bake()
    {
        // Create a new texture the same size as the sclera
        Texture2D combined = new Texture2D(scleraTexture.width, scleraTexture.height);
        
        // Copy sclera pixels
        combined.SetPixels(scleraTexture.GetPixels());
        
        // Loop through iris and overlay it
        // Note: You might need to adjust the offset if the iris isn't centered in the UV
        Color[] irisPixels = irisTexture.GetPixels();
        int startX = (scleraTexture.width - irisTexture.width) / 2;
        int startY = (scleraTexture.height - irisTexture.height) / 2;

        for (int y = 0; y < irisTexture.height; y++)
        {
            for (int x = 0; x < irisTexture.width; x++)
            {
                Color irisCol = irisPixels[y * irisTexture.width + x];
                if (irisCol.a > 0.1f) // Simple alpha blending
                {
                    combined.SetPixel(startX + x, startY + y, irisCol);
                }
            }
        }

        combined.Apply();
        byte[] bytes = combined.EncodeToPNG();
        File.WriteAllBytes(Application.dataPath + "/" + saveName + ".png", bytes);
        Debug.Log("Saved baked eye to: " + Application.dataPath + "/" + saveName + ".png");
    }
}