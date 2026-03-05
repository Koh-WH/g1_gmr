#!/usr/bin/env python3
"""
Converts a Mixamo BVH file to LAFAN1-compatible format for use with
general_motion_retargeting's bvh_to_robot.py.

Four things are fixed:
  1. 'mixamorig:' prefix stripped from all joint names.
  2. Non-root joints: CHANNELS 6 → CHANNELS 3 (rotation only);
     position values removed from every frame line.
  3. 'LeftToeBase' / 'RightToeBase' renamed to 'LeftToe' / 'RightToe'
     (LAFAN1 convention, required for LeftFootMod/RightFootMod synthesis).
  4. Root XZ re-centred to world origin (frame-0 XZ offset subtracted).

Optional:
  --in_place   Also remove the XZ drift trajectory so the motion stays
               on the spot (useful when the performer walked during recording).

Usage:
  python convert_mixamo_to_lafan1.py input_mixamo.bvh output_lafan1.bvh [--in_place]
"""

import sys
import re

RENAME_MAP = {
    "LeftToeBase":  "LeftToe",
    "RightToeBase": "RightToe",
}


def clean_name(raw: str) -> str:
    name = raw.replace("mixamorig:", "")
    return RENAME_MAP.get(name, name)


def convert(input_path: str, output_path: str, in_place: bool = False):
    with open(input_path, "r", errors="replace") as f:
        raw = f.read()

    lines = raw.replace("\r\n", "\n").replace("\r", "\n").split("\n")

    # ------------------------------------------------------------------
    # PASS 1 – collect joint order, root status, original channel counts
    # ------------------------------------------------------------------
    joint_order = []
    is_root = {}
    orig_chan = {}
    cur = None

    for line in lines:
        s = line.strip()
        if s == "MOTION":
            break
        m = re.match(r"(ROOT|JOINT)\s+(\S+)", s)
        if m:
            kind, raw_name = m.groups()
            name = clean_name(raw_name)
            cur = name
            joint_order.append(name)
            is_root[name] = (kind == "ROOT")
            continue
        mc = re.match(r"CHANNELS\s+(\d+)", s)
        if mc and cur:
            orig_chan[cur] = int(mc.group(1))

    drop = {j: (0 if is_root[j] else max(0, orig_chan.get(j, 3) - 3))
            for j in joint_order}

    total_orig = sum(orig_chan.get(j, 3) for j in joint_order)
    total_drop = sum(drop[j] for j in joint_order)

    print(f"Joints found : {len(joint_order)}")
    print(f"Root joint   : {[j for j, r in is_root.items() if r]}")
    print(f"Renamed      : {RENAME_MAP}")
    print(f"Values/frame : {total_orig} → {total_orig - total_drop} "
          f"({total_drop} position values removed from non-root joints)")

    # ------------------------------------------------------------------
    # PASS 2 – collect all frame data to compute the reference XZ offset
    # Root channels in Mixamo: Xposition Yposition Zposition (then rotation)
    # ------------------------------------------------------------------
    frame_data_lines = []
    in_motion = False
    for line in lines:
        s = line.strip()
        if s == "MOTION":
            in_motion = True
            continue
        if in_motion and (s.startswith("Frames:") or s.startswith("Frame Time:") or not s):
            continue
        if in_motion and s:
            frame_data_lines.append(s)

    if not frame_data_lines:
        print("ERROR: No frame data found.")
        sys.exit(1)

    first_vals = frame_data_lines[0].split()
    origin_x = float(first_vals[0])
    origin_z = float(first_vals[2])   # Y (height) stays untouched

    print(f"\nFrame-0 root XYZ : ({float(first_vals[0]):.3f}, {float(first_vals[1]):.3f}, {float(first_vals[2]):.3f})")
    print(f"Subtracting XZ offset : ΔX={origin_x:.3f}  ΔZ={origin_z:.3f}")

    if in_place:
        # Compute X and Z for every frame (after removing origin offset)
        traj_x = [float(l.split()[0]) - origin_x for l in frame_data_lines]
        traj_z = [float(l.split()[2]) - origin_z for l in frame_data_lines]
        total_x_range = max(traj_x) - min(traj_x)
        total_z_range = max(traj_z) - min(traj_z)
        print(f"--in_place : also removing per-frame XZ drift "
              f"(X range {total_x_range:.1f} cm, Z range {total_z_range:.1f} cm)")

    # ------------------------------------------------------------------
    # PASS 3 – rewrite the file
    # ------------------------------------------------------------------
    out_lines = []
    in_motion = False
    frames_written = 0
    cur = None
    frame_idx = 0

    for line in lines:
        s = line.strip()

        if s == "MOTION":
            in_motion = True
            out_lines.append(line)
            continue

        # ---- HIERARCHY section ----
        if not in_motion:
            m = re.match(r"(\s*)(ROOT|JOINT)\s+(\S+)(.*)", line)
            if m:
                indent, kind, raw_name, rest = m.groups()
                name = clean_name(raw_name)
                cur = name
                out_lines.append(f"{indent}{kind} {name}{rest}")
                continue

            mc = re.match(r"(\s*)CHANNELS\s+\d+\s+(.+)", line)
            if mc and cur is not None:
                indent = mc.group(1)
                tokens = mc.group(2).split()
                if is_root.get(cur, False):
                    out_lines.append(line)
                else:
                    rot = [t for t in tokens if t.lower().endswith("rotation")]
                    out_lines.append(
                        f"{indent}CHANNELS {len(rot)} {' '.join(rot)}"
                    )
                continue

            out_lines.append(line)

        # ---- MOTION section ----
        else:
            if s.startswith("Frames:") or s.startswith("Frame Time:") or not s:
                out_lines.append(line)
                continue

            values = s.split()
            idx, new_values = 0, []

            for j in joint_order:
                n = orig_chan.get(j, 3)
                chunk = values[idx: idx + n]
                idx += n

                if is_root.get(j, False):
                    floats = [float(v) for v in chunk]
                    # Always subtract frame-0 XZ offset
                    floats[0] -= origin_x
                    floats[2] -= origin_z
                    # Optionally strip per-frame XZ trajectory too
                    if in_place:
                        floats[0] -= traj_x[frame_idx]
                        floats[2] -= traj_z[frame_idx]
                    new_values.extend(f"{v:.6g}" for v in floats)
                else:
                    new_values.extend(chunk[drop[j]:])

            new_values.extend(values[idx:])
            out_lines.append(" ".join(new_values))
            frames_written += 1
            frame_idx += 1

    with open(output_path, "w") as f:
        f.write("\n".join(out_lines))

    mode_tag = " [IN-PLACE]" if in_place else ""
    print(f"\n✅  Done!{mode_tag}  Written to: {output_path}")
    print(f"    Frames written : {frames_written}")
    print()
    print("Run the retargeter (copy bvh_mixamo_to_g1.json into the ik_configs folder first):")
    print(f"  python bvh_to_robot.py \\")
    print(f"    --bvh_file {output_path} \\")
    print(f"    --robot unitree_g1 \\")
    print(f"    --format mixamo \\")
    print(f"    --rate_limit \\")
    print(f"    --save_path output/starjumps_g1.pkl")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(f"Usage: python {sys.argv[0]} <input_mixamo.bvh> <output_lafan1.bvh> [--in_place]")
        sys.exit(1)
    in_place = "--in_place" in sys.argv
    convert(sys.argv[1], sys.argv[2], in_place=in_place)