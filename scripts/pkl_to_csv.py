import pickle
import numpy as np
import argparse
import sys
import os

def convert_pkl_to_csv(input_path, output_path):
    print(f"📂 Opening {input_path}...")
    
    if not os.path.exists(input_path):
        print(f"❌ Error: File not found: {input_path}")
        sys.exit(1)

    with open(input_path, 'rb') as f:
        data = pickle.load(f)

    # --- 1. Extract Data (Handling GMR Structure) ---
    # GMR saves keys: 'root_pos', 'root_rot', 'dof_pos'
    
    # Root Position
    if 'root_pos' in data:
        root_pos = data['root_pos']
    elif 'root_trans' in data:
        root_pos = data['root_trans']
    else:
        print(f"❌ Error: Key 'root_pos' not found. Available: {list(data.keys())}")
        sys.exit(1)

    # Root Rotation
    if 'root_rot' in data:
        root_rot = data['root_rot']
    else:
        print(f"❌ Error: Key 'root_rot' not found.")
        sys.exit(1)

    # Joint Angles
    if 'dof_pos' in data:
        dof_pos = data['dof_pos']
    elif 'qpos' in data:
        dof_pos = data['qpos']
    else:
        print(f"❌ Error: Key 'dof_pos' not found.")
        sys.exit(1)

    # --- 2. Validation & Stacking ---
    n_frames = root_pos.shape[0]
    print(f"✅ Found {n_frames} frames.")
    
    # GMR script (gvhmr_to_robot.py) already converts rotation to [x, y, z, w].
    # We just stack them: Pos(3) + Rot(4) + Joints(29) = 36 columns
    final_data = np.hstack([root_pos, root_rot, dof_pos])

    # --- 3. Save ---
    print(f"💾 Saving to {output_path}...")
    np.savetxt(output_path, final_data, delimiter=",", fmt="%.6f")
    print("🚀 Done! Ready for MJLab.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, required=True, help="Input .pkl file")
    parser.add_argument("--output", type=str, default=None, help="Output .csv file")
    args = parser.parse_args()

    # Auto-generate output name if not provided
    if args.output is None:
        args.output = args.input.replace(".pkl", ".csv")

    convert_pkl_to_csv(args.input, args.output)