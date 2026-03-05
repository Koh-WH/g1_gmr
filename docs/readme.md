Edited these files:  
GMR/general_motion_retargeting/ik_configs/bvh_mixamo_to_g1.json  
GMR/general_motion_retargeting/utils/lafan1.py  
GMR/general_motion_retargeting/params.py  
GMR/scripts/bvh_to_robot.py  
GMR/scripts/convert_mixamo_to_lafan1.py  
  

Created a script to converts Rebocap Mixamo BVH file to LAFAN1-compatible format for use with general_motion_retargeting's bvh_to_robot.py.  
```bash
python scripts/convert_mixamo_to_lafan1.py /home/koh-wh/Downloads/NeutralPose.bvh /home/koh-wh/Downloads/NeutralPose_converted.bvh
python scripts/convert_mixamo_to_lafan1.py /home/koh-wh/Downloads/squats.bvh /home/koh-wh/Downloads/squats_converted.bvh
python scripts/convert_mixamo_to_lafan1.py /home/koh-wh/Downloads/starjumps.bvh /home/koh-wh/Downloads/starjumps_converted.bvh
```
  
Edited the original bvh_to_robot.py to accept mixamo format. Along with this, editing `lafan1.py`, `params.py` and the creation of `bvh_mixamo_to_g1.json` is needed.  
```bash
python scripts/bvh_to_robot.py     --bvh_file /home/koh-wh/Downloads/NeutralPose_converted.bvh     --robot unitree_g1     --format mixamo     --rate_limit     --save_path output/neutralpose_rebocap.pkl

python scripts/bvh_to_robot.py     --bvh_file /home/koh-wh/Downloads/squats_converted.bvh     --robot unitree_g1     --format mixamo     --rate_limit     --save_path output/squats_rebocap.pkl
python scripts/bvh_to_robot.py     --bvh_file /home/koh-wh/Downloads/starjumps_converted.bvh     --robot unitree_g1     --format mixamo     --rate_limit     --save_path output/starjumps_rebocap.pkl
```
  
This will create the mapping from rebocap bvh to the g1 robot and output in .pkl format.    
  