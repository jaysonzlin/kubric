import os

script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(script_dir)
output_dir = os.path.join(project_dir, "output")

required_files = [
    "metadata.json",
    "scene.blend",
    "scene.bullet",
    "pc.hdf5",
    "pc_trajectory.mp4"
]

all_ok = True
print("Checking sample directories...")

for i in range(1, 15):
    sample_name = f"sample_{i}"
    sample_dir = os.path.join(output_dir, sample_name)
    if not os.path.exists(sample_dir):
        print(f"[-] {sample_name}: Directory missing!")
        all_ok = False
        continue
        
    missing = []
    for f in required_files:
        path = os.path.join(sample_dir, f)
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            missing.append(f)
            
    # Also check if image files are present (at least some rgba and depth files)
    contents = os.listdir(sample_dir)
    rgba_files = [f for f in contents if f.startswith("rgba_")]
    depth_files = [f for f in contents if f.startswith("depth_")]
    
    if len(rgba_files) < 24:
        missing.append(f"rgba files (found {len(rgba_files)}/24)")
    if len(depth_files) < 24:
        missing.append(f"depth files (found {len(depth_files)}/24)")
        
    if missing:
        print(f"[-] {sample_name}: Missing or incomplete: {', '.join(missing)}")
        all_ok = False
    else:
        print(f"[+] {sample_name}: All files verified (HDF5 size: {os.path.getsize(os.path.join(sample_dir, 'pc.hdf5'))} bytes, MP4 size: {os.path.getsize(os.path.join(sample_dir, 'pc_trajectory.mp4'))} bytes)")

if all_ok:
    print("\nSUCCESS: All 14 samples are complete and contain all expected outputs!")
else:
    print("\nWARNING: Some samples are missing files or incomplete!")
