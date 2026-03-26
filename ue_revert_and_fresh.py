"""Revert FaceExport to disk version, then apply viseme keys fresh."""
import unreal

out = []

# Close current sequence
try:
    unreal.LevelSequenceEditorBlueprintLibrary.close_level_sequence()
    out.append("Closed sequence")
except:
    pass

seq_path = "/Game/MetaHumans/model4/Face/FaceExport"

# Try to reload/revert the asset
try:
    asset = unreal.load_asset(seq_path)
    # Check if dirty
    is_dirty = asset.modify(False) if hasattr(asset, 'modify') else 'unknown'
    out.append(f"Asset loaded: {asset.get_name()}")
except Exception as e:
    out.append(f"Load error: {e}")

# Try EditorAssetLibrary to revert
try:
    # Reimport won't work for sequences, try reload
    result = unreal.EditorLoadingAndSavingUtils.reload_packages(
        [unreal.find_package(seq_path)])
    out.append(f"Reload result: {result}")
except Exception as e:
    out.append(f"Reload error: {e}")

# Alternative: just check available methods
try:
    lib_methods = [m for m in dir(unreal.EditorAssetLibrary) if 'revert' in m.lower() or 'reload' in m.lower() or 'checkout' in m.lower()]
    out.append(f"EditorAssetLibrary revert methods: {lib_methods}")
except:
    pass

try:
    pkg_methods = [m for m in dir(unreal.PackageTools) if not m.startswith('_')]
    out.append(f"PackageTools methods: {pkg_methods}")
except:
    out.append("No PackageTools")

# Check EditorLoadingAndSavingUtils methods
try:
    save_methods = [m for m in dir(unreal.EditorLoadingAndSavingUtils) if not m.startswith('_')]
    out.append(f"EditorLoadingAndSavingUtils: {save_methods}")
except:
    pass

# Reopen
try:
    asset = unreal.load_asset(seq_path)
    unreal.LevelSequenceEditorBlueprintLibrary.open_level_sequence(asset)
    out.append("Reopened sequence")
except Exception as e:
    out.append(f"Reopen error: {e}")

# Check state
level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()
if level_seq:
    for b in level_seq.get_bindings():
        name = b.get_display_name()
        for t in b.get_tracks():
            dn = str(t.get_display_name())
            if "Face" in name:
                sections = t.get_sections()
                ch_count = len(sections[0].get_all_channels()) if sections else 0
                keyed = sum(1 for ch in sections[0].get_all_channels() if ch.get_num_keys() > 0) if sections else 0
                out.append(f"  {name}/{dn}: {ch_count} channels, {keyed} keyed")

open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
