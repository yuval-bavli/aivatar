import unreal

try:
    if unreal.EditorAssetLibrary.does_asset_exist("/Game/MetaHumans/model4/Face/FaceExport_Backup"):
        unreal.EditorAssetLibrary.delete_asset("/Game/MetaHumans/model4/Face/FaceExport_Backup")
    
    source_asset = unreal.EditorAssetLibrary.load_asset("/Game/MetaHumans/model4/Face/FaceExport")
    if getattr(unreal, 'AssetToolsHelpers', None):
        asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
        success = asset_tools.duplicate_asset("FaceExport_Backup", "/Game/MetaHumans/model4/Face", source_asset)
        if success:
            open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("Backup created: /Game/MetaHumans/model4/Face/FaceExport_Backup")
        else:
            open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("Failed to duplicate asset.")
    else:
        # Fallback if AssetToolsHelpers is not the right way in this version
        success = unreal.EditorAssetLibrary.duplicate_asset("/Game/MetaHumans/model4/Face/FaceExport", "/Game/MetaHumans/model4/Face/FaceExport_Backup")
        open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(f"Duplicated via EditorAssetLibrary: {success}")
except Exception as e:
    open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(f"Error during backup: {e}")
