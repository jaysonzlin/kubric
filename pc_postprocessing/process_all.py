import os
import subprocess

script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(script_dir)

blender_path = "/Applications/Blender.app/Contents/MacOS/Blender"
python_path = "/Users/jaysonlin/miniconda3/envs/pc_env/bin/python"

output_dir = os.path.join(project_dir, "output")
samples = sorted([d for d in os.listdir(output_dir) if d.startswith("sample_") and os.path.isdir(os.path.join(output_dir, d))], key=lambda s: int(s.split("_")[1]))

print(f"Found {len(samples)} samples to process: {samples}")

for sample in samples:
    sample_dir = os.path.join(output_dir, sample)
    blend_file = os.path.join(sample_dir, "scene.blend")
    if not os.path.exists(blend_file):
        print(f"Skipping {sample}: scene.blend not found.")
        continue
        
    print(f"\n========================================\nProcessing {sample}...\n========================================")
    
    # 1. Run generate_pc.py
    generate_pc_path = os.path.join(script_dir, "generate_pc.py")
    gen_cmd = [
        blender_path,
        "--background",
        blend_file,
        "--python",
        generate_pc_path,
        "--",
        "--sample_dir",
        sample_dir
    ]
    print(f"Running generator: {' '.join(gen_cmd)}")
    gen_res = subprocess.run(gen_cmd, capture_output=True, text=True)
    if gen_res.returncode != 0:
        print(f"Error running generate_pc.py on {sample}:")
        print(gen_res.stderr)
        continue
    else:
        print(gen_res.stdout)
        
    # 2. Run visualize_pc.py
    visualize_pc_path = os.path.join(script_dir, "visualize_pc.py")
    viz_cmd = [
        python_path,
        visualize_pc_path,
        "--sample_dir",
        sample_dir
    ]
    print(f"Running visualizer: {' '.join(viz_cmd)}")
    viz_res = subprocess.run(viz_cmd, capture_output=True, text=True)
    if viz_res.returncode != 0:
        print(f"Error running visualize_pc.py on {sample}:")
        print(viz_res.stderr)
    else:
        print(viz_res.stdout)

print("\nAll samples processed successfully!")
