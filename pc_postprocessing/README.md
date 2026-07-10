# Point Cloud Postprocessing

Generate point cloud trajectories and videos for Kubric samples under `output/`.

## Prerequisites

- Blender at `/Applications/Blender.app/Contents/MacOS/Blender`
- Conda env Python at `/Users/jaysonlin/miniconda3/envs/pc_env/bin/python`
- Each sample directory contains `scene.blend` and `metadata.json`

## Run All Samples

From the repository root:

```bash
python3 pc_postprocessing/process_all.py
```

This scans `output/sample_*` directories, then for each sample:

1. runs `generate_pc.py` in Blender to write `pc.hdf5`
2. runs `visualize_pc.py` in `pc_env` to write `pc_trajectory.mp4`

Generated files are saved next to the sample inputs:

```text
output/sample_N/pc.hdf5
output/sample_N/pc_trajectory.mp4
```

## Run One Sample

```bash
/Applications/Blender.app/Contents/MacOS/Blender --background output/sample_0/scene.blend --python pc_postprocessing/generate_pc.py -- --sample_dir output/sample_0
/Users/jaysonlin/miniconda3/envs/pc_env/bin/python pc_postprocessing/visualize_pc.py --sample_dir output/sample_0
```

## Verify Outputs

```bash
find output -maxdepth 2 \( -name pc.hdf5 -o -name pc_trajectory.mp4 \) -print
```

Blender may crash during Metal GPU detection when run inside a restricted sandbox. If that happens, run the same command from a normal terminal or allow Blender to run outside the sandbox.
