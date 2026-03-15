using UnityEngine;
using UnityEditor;

public static class ForceReimportTexture
{
    public static string Run()
    {
        string path = "Assets/Models/Avatar/Textures/T_Head_BC_VT_Brows.png";
        AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceUpdate);

        // Also verify the texture is loaded correctly
        var tex = AssetDatabase.LoadAssetAtPath<Texture2D>(path);
        if (tex == null) return $"ERROR: texture not found at {path}";

        // Read a pixel from the eyebrow region (Y=720 maps to texture pixel ~720 from top)
        // Unity textures have Y=0 at BOTTOM, so pixel y in Unity = tex.height - 1 - image_y
        int imgY = 720;
        int imgX = 595; // center of left brow
        int unityX = imgX;
        int unityY = tex.height - 1 - imgY;
        Color pixel = tex.GetPixel(unityX, unityY);

        // Also check the MATERIAL's texture
        var mat = AssetDatabase.LoadAssetAtPath<Material>(
            "Assets/Models/Avatar/Materials/MI_Face_Skin_Baked_LOD1_VT.mat");
        Texture matTex = mat != null ? mat.mainTexture : null;

        return $"Reimported. Tex={tex.name} {tex.width}x{tex.height}\n" +
               $"Pixel at imgXY=({imgX},{imgY}) -> unityXY=({unityX},{unityY}): " +
               $"R={pixel.r:F3} G={pixel.g:F3} B={pixel.b:F3} A={pixel.a:F3}\n" +
               $"Material mainTexture: {(matTex != null ? matTex.name : "null")}";
    }
}
