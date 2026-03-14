Shader "Aivatar/EyebrowOverlay"
{
    Properties
    {
        _BaseMap ("Texture", 2D) = "white" {}
        _BaseColor ("Color", Color) = (0.14, 0.09, 0.06, 1)
        _Cutoff ("Alpha Cutoff", Range(0,1)) = 0.03
    }
    SubShader
    {
        Tags { "RenderType"="TransparentCutout" "Queue"="Geometry+100" "RenderPipeline"="UniversalPipeline" }
        LOD 100

        Pass
        {
            Name "EyebrowPass"
            Tags { "LightMode"="UniversalForward" }

            ZTest Always
            ZWrite Off
            Cull Off

            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"

            struct Attributes
            {
                float4 positionOS : POSITION;
                float2 uv : TEXCOORD0;
                float3 normalOS : NORMAL;
            };

            struct Varyings
            {
                float4 positionHCS : SV_POSITION;
                float2 uv : TEXCOORD0;
                float3 normalWS : TEXCOORD1;
                float3 positionWS : TEXCOORD2;
            };

            TEXTURE2D(_BaseMap);
            SAMPLER(sampler_BaseMap);

            CBUFFER_START(UnityPerMaterial)
                float4 _BaseMap_ST;
                half4 _BaseColor;
                half _Cutoff;
            CBUFFER_END

            Varyings vert(Attributes IN)
            {
                Varyings OUT;
                OUT.positionHCS = TransformObjectToHClip(IN.positionOS.xyz);
                OUT.uv = TRANSFORM_TEX(IN.uv, _BaseMap);
                OUT.normalWS = TransformObjectToWorldNormal(IN.normalOS);
                OUT.positionWS = TransformObjectToWorld(IN.positionOS.xyz);
                return OUT;
            }

            half4 frag(Varyings IN) : SV_Target
            {
                half4 texColor = SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, IN.uv);

                // Alpha test
                clip(texColor.a - _Cutoff);

                // Simple directional lighting
                Light mainLight = GetMainLight();
                float3 normalWS = normalize(IN.normalWS);
                half NdotL = saturate(dot(normalWS, mainLight.direction));
                half3 ambient = half3(0.3, 0.3, 0.3);
                half3 lighting = ambient + mainLight.color * NdotL * 0.7;

                half3 color = texColor.rgb * _BaseColor.rgb * lighting;
                return half4(color, 1);
            }
            ENDHLSL
        }
    }
}
