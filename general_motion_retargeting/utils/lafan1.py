import numpy as np
from scipy.spatial.transform import Rotation as R

import general_motion_retargeting.utils.lafan_vendor.utils as utils
from general_motion_retargeting.utils.lafan_vendor.extract import read_bvh


def load_bvh_file(bvh_file, format="lafan1"):
    """
    Must return a dictionary with the following structure:
    {
        "Hips": (position, orientation),
        "Spine": (position, orientation),
        ...
    }
    """
    data = read_bvh(bvh_file)
    global_data = utils.quat_fk(data.quats, data.pos, data.parents)

    if format == "mixamo":
        # Matches COORDINATE_REMAP from config_local_joints.py
        # Unity/Mixamo: X(side)->MuJoCo Y,  Y(up)->MuJoCo Z,  Z(forward)->MuJoCo X
        rotation_matrix = np.array([[0, 0, 1], [1, 0, 0], [0, 1, 0]])
    else:
        rotation_matrix = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]])
    rotation_quat = R.from_matrix(rotation_matrix).as_quat(scalar_first=True)

    frames = []
    for frame in range(data.pos.shape[0]):
        result = {}
        for i, bone in enumerate(data.bones):
            orientation = utils.quat_mul(rotation_quat, global_data[0][frame, i])
            position = global_data[1][frame, i] @ rotation_matrix.T / 100  # cm to m
            result[bone] = [position, orientation]
            
        if format in ("lafan1", "mixamo"):   # ← mixamo uses same toe names as lafan1
            result["LeftFootMod"] = [result["LeftFoot"][0], result["LeftToe"][1]]
            result["RightFootMod"] = [result["RightFoot"][0], result["RightToe"][1]]
        elif format == "nokov":
            result["LeftFootMod"] = [result["LeftFoot"][0], result["LeftToeBase"][1]]
            result["RightFootMod"] = [result["RightFoot"][0], result["RightToeBase"][1]]
        else:
            raise ValueError(f"Invalid format: {format}")
            
        frames.append(result)
    
    # ── Ground correction for mixamo ─────────────────────────────────────────
    # The Mixamo FK places feet well above Z=0 due to bind-pose orientation.
    # Find the lowest foot point across ALL frames and shift every joint
    # position down by that amount so the human's feet touch Z=0.
    if format == "mixamo":
        min_foot_z = min(
            min(f["LeftFoot"][0][2]  for f in frames),
            min(f["RightFoot"][0][2] for f in frames),
        )
        for f in frames:
            for key in f:
                pos = f[key][0]
                f[key][0] = np.array([pos[0], pos[1], pos[2] - min_foot_z])
    # ─────────────────────────────────────────────────────────────────────────


    # human_height = result["Head"][0][2] - min(result["LeftFootMod"][0][2], result["RightFootMod"][0][2])
    # human_height = human_height + 0.2  # cm to m
    human_height = 1.75  # cm to m

    return frames, human_height


