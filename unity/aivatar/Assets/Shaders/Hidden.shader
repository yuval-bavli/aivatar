Shader "Aivatar/Hidden"
{
    // Renders nothing - used to hide submeshes that can't be disabled directly
    SubShader
    {
        Tags { "RenderType"="Transparent" "Queue"="Transparent" }
        Pass
        {
            ZWrite Off
            ColorMask 0
            Cull Off
        }
    }
}
