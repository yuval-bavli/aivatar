"""
texture_editor.py — Direct texture manipulation using Pillow.

Approach 2: Instead of tweaking material properties, directly modify the texture
files to fix visual issues:

1. Eyelash texture: Modify the alpha channel to make strands thinner/softer
2. Eyebrow texture: Paint realistic eyebrows onto the face base color texture
3. Hair texture: Adjust color/contrast of hair albedo

This works at the pixel level — something material property tweaking can never do.

Usage:
    python texture_editor.py fix-eyelashes [--thin-factor 0.6]
    python texture_editor.py fix-eyebrows [--strength 0.3] [--color 0.25,0.18,0.12]
    python texture_editor.py fix-all
"""

from __future__ import annotations

import pathlib
import shutil
import datetime
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageEnhance

_REPO_ROOT = pathlib.Path(__file__).parent.parent.resolve()
_TEXTURES_DIR = _REPO_ROOT / "unity" / "aivatar" / "Assets" / "Models" / "Avatar" / "Textures"
_BACKUP_DIR = pathlib.Path(__file__).parent / "tex_backups"


def _backup(path: pathlib.Path) -> None:
    """Create a timestamped backup before editing."""
    if not path.exists():
        return
    _BACKUP_DIR.mkdir(exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = _BACKUP_DIR / f"{path.stem}_{stamp}{path.suffix}"
    shutil.copy2(path, dest)
    print(f"[texture_editor] Backup: {dest}", file=sys.stderr)


# ── Eyelash Texture Fixes ─────────────────────────────────────────────────


def fix_eyelash_alpha(
    thin_factor: float = 0.5,
    softness: float = 1.5,
    texture_name: str = "EyelashThin.png",
) -> pathlib.Path:
    """
    Make eyelashes thinner by modifying the alpha channel.

    thin_factor: 0.0 = invisible, 1.0 = original thickness
                 Values < 1.0 make lashes thinner by raising the alpha threshold.
    softness: Gaussian blur radius applied to alpha for softer edges.

    Returns the path to the modified texture.
    """
    # Try to find the eyelash texture
    tex_path = _TEXTURES_DIR / texture_name
    if not tex_path.exists():
        # Try the original MetaHuman eyelash texture
        for candidate in _TEXTURES_DIR.glob("*yelash*"):
            tex_path = candidate
            break
        else:
            raise FileNotFoundError(f"No eyelash texture found in {_TEXTURES_DIR}")

    _backup(tex_path)

    img = Image.open(tex_path).convert("RGBA")
    r, g, b, a = img.split()

    # Apply thinning: reduce alpha values below a threshold to 0
    # This effectively narrows the visible area of each lash strand
    import numpy as np

    alpha_arr = np.array(a, dtype=np.float32) / 255.0

    # Step 1: Apply power curve to steepen the alpha falloff
    # thin_factor < 1.0 makes the transition sharper (thinner strands)
    if thin_factor < 1.0:
        # Raise alpha to a power > 1 to make thin areas transparent
        power = 1.0 / max(thin_factor, 0.1)
        alpha_arr = np.power(alpha_arr, power)

    # Step 2: Apply minimum threshold (remove very faint pixels)
    threshold = 0.15
    alpha_arr[alpha_arr < threshold] = 0.0

    # Step 3: Rescale remaining values
    mask = alpha_arr > 0
    if mask.any():
        min_val = alpha_arr[mask].min()
        alpha_arr[mask] = (alpha_arr[mask] - min_val) / (1.0 - min_val + 1e-8)

    # Convert back
    a_new = Image.fromarray((alpha_arr * 255).astype(np.uint8), mode="L")

    # Step 4: Optional softness blur for anti-aliasing
    if softness > 0:
        a_new = a_new.filter(ImageFilter.GaussianBlur(radius=softness))

    img_out = Image.merge("RGBA", (r, g, b, a_new))

    out_path = _TEXTURES_DIR / "EyelashThin.png"
    img_out.save(out_path, "PNG")
    print(f"[texture_editor] Eyelash texture saved: {out_path}", file=sys.stderr)
    return out_path


def create_eyelash_texture_from_original(
    thin_factor: float = 0.4,
) -> pathlib.Path:
    """
    Create a thinner eyelash texture from the original MetaHuman eyelash albedo.

    If no eyelash-specific texture exists, creates one from the base map
    referenced in the material file.
    """
    # Look for any existing eyelash texture
    candidates = list(_TEXTURES_DIR.glob("*yelash*")) + list(_TEXTURES_DIR.glob("*Eyelash*"))
    if candidates:
        return fix_eyelash_alpha(thin_factor=thin_factor, texture_name=candidates[0].name)

    # No eyelash texture found — create a simple procedural one
    print("[texture_editor] No eyelash texture found, creating procedural one", file=sys.stderr)
    import numpy as np

    # Create a 512x256 texture with thin dark strands on transparent background
    w, h = 512, 256
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Draw thin curved lash strands
    import math
    rng = __import__("random").Random(42)

    for row in range(2):  # Top and bottom row of lashes
        y_base = 60 + row * 120
        for i in range(40):
            x_start = 10 + i * (w - 20) // 40
            length = rng.randint(20, 50)
            angle = math.radians(rng.uniform(70, 110))
            thickness = 1

            for t in range(length):
                x = int(x_start + t * math.cos(angle) + rng.gauss(0, 0.3))
                y = int(y_base - t * math.sin(angle))
                alpha = int(255 * (1 - t / length) * 0.8)
                if 0 <= x < w and 0 <= y < h:
                    draw.point((x, y), fill=(20, 15, 10, alpha))

    # Blur slightly for anti-aliasing
    img = img.filter(ImageFilter.GaussianBlur(radius=0.5))

    out_path = _TEXTURES_DIR / "EyelashThin.png"
    img.save(out_path, "PNG")
    print(f"[texture_editor] Procedural eyelash texture: {out_path}", file=sys.stderr)
    return out_path


# ── Eyebrow Texture Fixes ─────────────────────────────────────────────────


def paint_eyebrows(
    strength: float = 0.35,
    color: tuple = (0.28, 0.20, 0.14),
    thickness_px: int = 8,
    num_hair_strokes: int = 60,
    source_texture: str = "T_Head_BC_VT.PNG",
) -> pathlib.Path:
    """
    Paint realistic eyebrows onto the face base color texture using Pillow.

    This is more reliable than the C# BakeEyebrows approach because:
    - Runs entirely in Python (no Unity compile cycle)
    - Uses proper anti-aliasing and blending
    - Can use reference-image-guided placement

    Parameters:
        strength: Blend strength (0=invisible, 1=fully opaque)
        color: RGB tuple (0-1 range) for eyebrow base color
        thickness_px: Thickness in pixels (at 8192 resolution)
        num_hair_strokes: Number of individual hair strokes per eyebrow
        source_texture: Original face texture to paint onto

    Returns path to the output texture.
    """
    import numpy as np

    src_path = _TEXTURES_DIR / source_texture
    if not src_path.exists():
        # Try case-insensitive search
        for f in _TEXTURES_DIR.iterdir():
            if f.name.lower() == source_texture.lower():
                src_path = f
                break
        else:
            raise FileNotFoundError(f"Source texture not found: {src_path}")

    img = Image.open(src_path).convert("RGB")
    w, h = img.size
    scale = w / 8192.0

    # UV coordinates for eyebrows (from MetaHuman UV mapping)
    # Right eyebrow (viewer's left)
    r_start = (int(698 * scale), int(1455 * scale))
    r_end = (int(658 * scale), int(1310 * scale))
    r_peak_y = int(1510 * scale)

    # Left eyebrow (viewer's right)
    l_start = (int(1362 * scale), int(1455 * scale))
    l_end = (int(1402 * scale), int(1310 * scale))
    l_peak_y = int(1510 * scale)

    # Convert to numpy for manipulation
    arr = np.array(img, dtype=np.float32) / 255.0
    brow_color = np.array(color, dtype=np.float32)

    def _bezier_point(t: float, p0, p1, p2):
        """Quadratic bezier curve point."""
        x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t ** 2 * p2[0]
        y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t ** 2 * p2[1]
        return x, y

    def _paint_brow(start, end, peak_y, flip=False):
        """Paint one eyebrow using bezier curve + hair strokes."""
        mid_x = (start[0] + end[0]) / 2
        control = (mid_x, peak_y)

        rng = __import__("random").Random(42 if not flip else 137)

        # Base brow shape: thick bezier stroke
        thickness = thickness_px * scale
        for i in range(200):
            t = i / 200.0
            cx, cy = _bezier_point(t, start, control, end)

            # Taper: thickest at 30-40% along, thin at ends
            taper = 1.0 - 0.7 * abs(t - 0.35) / max(0.65, 1e-8)
            taper = max(taper, 0.2)
            r = thickness * taper

            ir = int(np.ceil(r))
            for dy in range(-ir, ir + 1):
                for dx in range(-ir, ir + 1):
                    px = int(cx) + dx
                    py = int(cy) + dy
                    if px < 0 or px >= w or py < 0 or py >= h:
                        continue
                    dist = np.sqrt(dx * dx + dy * dy)
                    if dist > r:
                        continue
                    falloff = (1.0 - dist / r) ** 2
                    blend = strength * falloff * 0.6
                    arr[py, px] = arr[py, px] * (1 - blend) + brow_color * blend

        # Individual hair strokes for realism
        import math
        for _ in range(num_hair_strokes):
            t = rng.uniform(0.05, 0.95)
            cx, cy = _bezier_point(t, start, control, end)

            # Hair direction: roughly upward with slight outward angle
            angle = math.radians(rng.uniform(65, 115))
            hair_len = int(rng.uniform(3, 12) * scale)
            hair_strength = strength * rng.uniform(0.2, 0.5)

            # Slight variation in hair color
            hair_col = brow_color * rng.uniform(0.85, 1.15)
            hair_col = np.clip(hair_col, 0, 1)

            for step in range(hair_len):
                hx = int(cx + step * math.cos(angle) + rng.gauss(0, 0.5))
                hy = int(cy - step * math.sin(angle))
                if 0 <= hx < w and 0 <= hy < h:
                    fade = 1.0 - step / hair_len
                    blend = hair_strength * fade
                    arr[hy, hx] = arr[hy, hx] * (1 - blend) + hair_col * blend

    _paint_brow(r_start, r_end, r_peak_y, flip=False)
    _paint_brow(l_start, l_end, l_peak_y, flip=True)

    # Convert back and save
    out_arr = (np.clip(arr, 0, 1) * 255).astype(np.uint8)
    out_img = Image.fromarray(out_arr, mode="RGB")

    out_path = _TEXTURES_DIR / "T_Head_BC_VT_Brows.png"
    _backup(out_path)
    out_img.save(out_path, "PNG")
    print(f"[texture_editor] Eyebrows painted: {out_path}", file=sys.stderr)
    return out_path


# ── Hair Texture Fixes ─────────────────────────────────────────────────────


def adjust_hair_texture(
    contrast: float = 1.2,
    brightness: float = 0.9,
    texture_name: str | None = None,
) -> pathlib.Path | None:
    """
    Adjust hair texture contrast and brightness.

    Makes hair look less flat/polygonal by increasing contrast between
    strand highlights and shadows.
    """
    if texture_name:
        tex_path = _TEXTURES_DIR / texture_name
    else:
        # Auto-detect hair texture
        candidates = [f for f in _TEXTURES_DIR.iterdir()
                       if "hair" in f.name.lower() and f.suffix.lower() in (".png", ".tga", ".jpg")]
        if not candidates:
            print("[texture_editor] No hair texture found to adjust", file=sys.stderr)
            return None
        tex_path = candidates[0]

    _backup(tex_path)

    img = Image.open(tex_path)
    if img.mode == "RGBA":
        r, g, b, a = img.split()
        rgb = Image.merge("RGB", (r, g, b))
    else:
        rgb = img.convert("RGB")
        a = None

    # Adjust contrast
    if contrast != 1.0:
        rgb = ImageEnhance.Contrast(rgb).enhance(contrast)

    # Adjust brightness
    if brightness != 1.0:
        rgb = ImageEnhance.Brightness(rgb).enhance(brightness)

    # Recombine with alpha
    if a is not None:
        r, g, b = rgb.split()
        img_out = Image.merge("RGBA", (r, g, b, a))
    else:
        img_out = rgb

    img_out.save(tex_path)
    print(f"[texture_editor] Hair texture adjusted: {tex_path}", file=sys.stderr)
    return tex_path


# ── Combined Fix ───────────────────────────────────────────────────────────


def fix_all(
    eyelash_thin_factor: float = 0.5,
    eyebrow_strength: float = 0.35,
    eyebrow_color: tuple = (0.28, 0.20, 0.14),
    hair_contrast: float = 1.2,
) -> dict:
    """Apply all texture-level fixes. Returns dict of results."""
    results = {}

    try:
        results["eyelashes"] = str(fix_eyelash_alpha(thin_factor=eyelash_thin_factor))
    except Exception as e:
        results["eyelashes"] = f"ERROR: {e}"
        try:
            results["eyelashes"] = str(create_eyelash_texture_from_original(thin_factor=eyelash_thin_factor))
        except Exception as e2:
            results["eyelashes"] = f"ERROR: {e2}"

    try:
        results["eyebrows"] = str(paint_eyebrows(strength=eyebrow_strength, color=eyebrow_color))
    except Exception as e:
        results["eyebrows"] = f"ERROR: {e}"

    try:
        r = adjust_hair_texture(contrast=hair_contrast)
        results["hair"] = str(r) if r else "No hair texture found"
    except Exception as e:
        results["hair"] = f"ERROR: {e}"

    return results


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Texture-level MetaHuman fixes")
    sub = parser.add_subparsers(dest="command")

    p_lash = sub.add_parser("fix-eyelashes")
    p_lash.add_argument("--thin-factor", type=float, default=0.5)

    p_brow = sub.add_parser("fix-eyebrows")
    p_brow.add_argument("--strength", type=float, default=0.35)
    p_brow.add_argument("--color", type=str, default="0.28,0.20,0.14")

    p_hair = sub.add_parser("fix-hair")
    p_hair.add_argument("--contrast", type=float, default=1.2)
    p_hair.add_argument("--brightness", type=float, default=0.9)

    p_all = sub.add_parser("fix-all")

    args = parser.parse_args()

    if args.command == "fix-eyelashes":
        fix_eyelash_alpha(thin_factor=args.thin_factor)
    elif args.command == "fix-eyebrows":
        color = tuple(float(x) for x in args.color.split(","))
        paint_eyebrows(strength=args.strength, color=color)
    elif args.command == "fix-hair":
        adjust_hair_texture(contrast=args.contrast, brightness=args.brightness)
    elif args.command == "fix-all":
        results = fix_all()
        print(json.dumps(results, indent=2))
    else:
        parser.print_help()
