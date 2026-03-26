"""
Test: directly set morph targets / blend shapes on the Face mesh to verify
the face CAN be deformed. This bypasses the sequencer entirely.
"""
import unreal, io

out = io.StringIO()
def p(msg=""): out.write(str(msg) + "\n")

# Find BP_model4's Face component
actors = unreal.EditorLevelLibrary.get_all_level_actors()
face_smc = None
for a in actors:
    if "BP_model4" in a.get_actor_label():
        comps = a.get_components_by_class(unreal.SkeletalMeshComponent)
        for c in comps:
            if c.get_name() == "Face":
                face_smc = c
                break
        break

if not face_smc:
    p("ERROR: Face SkeletalMeshComponent not found")
    open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(out.getvalue())
    raise SystemExit

p(f"Found Face component: {face_smc.get_name()}")

# List morph target names
try:
    morph_names = face_smc.get_morph_target_list()
    p(f"Morph targets: {len(morph_names)}")
    # Show first 30 and any with 'jaw' or 'mouth'
    jaw_morphs = [n for n in morph_names if 'jaw' in str(n).lower() or 'mouth' in str(n).lower() or 'open' in str(n).lower()]
    p(f"\nJaw/mouth morphs ({len(jaw_morphs)}):")
    for n in jaw_morphs[:20]:
        p(f"  {n}")

    p(f"\nFirst 20 morphs:")
    for n in list(morph_names)[:20]:
        p(f"  {n}")
except Exception as e:
    p(f"get_morph_target_list error: {e}")

# Try listing morph targets via skeletal mesh asset
try:
    mesh = face_smc.get_skeletal_mesh_asset()
    p(f"\nSkeletal mesh: {mesh.get_name()}")
    # Try to get morph targets
    morphs = mesh.get_morph_targets()
    p(f"Morph targets from mesh: {len(morphs)}")
    for m in morphs[:20]:
        p(f"  {m.get_name()}")
except Exception as e:
    p(f"Mesh morph targets: {e}")

# Try setting a morph target value directly
try:
    face_smc.set_morph_target("jawOpen", 1.0)
    p("\nset_morph_target('jawOpen', 1.0) -> OK")
except Exception as e:
    p(f"\nset_morph_target jawOpen error: {e}")

# Try FACS naming convention
try:
    face_smc.set_morph_target("CTRL_expressions_jawOpen", 1.0)
    p("set_morph_target('CTRL_expressions_jawOpen', 1.0) -> OK")
except Exception as e:
    p(f"CTRL_expressions_jawOpen: {e}")

p("\n=== DONE ===")
open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(out.getvalue())
