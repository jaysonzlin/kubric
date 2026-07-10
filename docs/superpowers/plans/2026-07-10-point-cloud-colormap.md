# Point Cloud Colormap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace solid point-cloud colors with stable per-point `viridis` colors derived from each object's relative frame-0 height, then render only `datasets/2_sample_1` to a separate preview video.

**Architecture:** A pure helper in the existing visualizer converts frame-0 heights into per-object normalized RGBA arrays, including a midpoint fallback for zero-height ranges. The rendering loop computes these arrays once, reuses them for every frame, and adds one shared relative-height colorbar. A CLI output-filename option preserves the original video while allowing the requested preview render.

**Tech Stack:** Python 3, NumPy, Matplotlib 3D scatter, h5py, imageio/FFmpeg, standard-library `unittest`

## Global Constraints

- Normalize frame-0 Z values independently for each object to the range 0–1.
- Use Matplotlib's perceptually uniform `viridis` colormap.
- Keep each point's color fixed throughout the trajectory.
- Map constant frame-0 heights to the colormap midpoint, 0.5.
- Label the shared colorbar `Relative initial height`.
- Preserve `datasets/2_sample_1/pc_trajectory.mp4` and write the preview to `datasets/2_sample_1/pc_trajectory_colormap.mp4`.
- Reuse `datasets/2_sample_1/pc.hdf5`; do not generate point clouds or render other samples.
- Do not create a PNG preview deliverable.

---

### Task 1: Stable Per-Point Colormap and Preview Output Option

**Files:**
- Create: `test/test_pc_postprocessing.py`
- Modify: `pc_postprocessing/visualize_pc.py:1-100`

**Interfaces:**
- Consumes: `pc_data: numpy.ndarray` shaped `(frames, objects, points, 3)`.
- Produces: `compute_point_colors(pc_data, cmap_name="viridis") -> numpy.ndarray` shaped `(objects, points, 4)` and CLI option `--output_filename: str` with default `pc_trajectory.mp4`.

- [ ] **Step 1: Write failing tests for independent normalization and the constant-height fallback**

```python
import unittest

import matplotlib.pyplot as plt
import numpy as np

from pc_postprocessing.visualize_pc import compute_point_colors


class ComputePointColorsTest(unittest.TestCase):
    def test_normalizes_initial_height_independently_per_object(self):
        pc_data = np.zeros((2, 2, 3, 3), dtype=np.float32)
        pc_data[0, 0, :, 2] = [0.0, 1.0, 2.0]
        pc_data[0, 1, :, 2] = [10.0, 20.0, 30.0]
        pc_data[1, :, :, 2] = 100.0

        colors = compute_point_colors(pc_data)

        expected = plt.get_cmap("viridis")(np.array([0.0, 0.5, 1.0]))
        self.assertEqual(colors.shape, (2, 3, 4))
        np.testing.assert_allclose(colors[0], expected)
        np.testing.assert_allclose(colors[1], expected)

    def test_uses_colormap_midpoint_for_constant_initial_height(self):
        pc_data = np.zeros((2, 1, 3, 3), dtype=np.float32)
        pc_data[0, 0, :, 2] = 7.0
        pc_data[1, 0, :, 2] = [1.0, 2.0, 3.0]

        colors = compute_point_colors(pc_data)

        expected = plt.get_cmap("viridis")(np.full(3, 0.5))
        np.testing.assert_allclose(colors[0], expected)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the focused tests and verify that the helper is missing**

Run:

```bash
MPLCONFIGDIR=/tmp/matplotlib /Users/jaysonlin/miniconda3/envs/pc_env/bin/python -m unittest test.test_pc_postprocessing -v
```

Expected: test discovery fails with `ImportError: cannot import name 'compute_point_colors'`.

- [ ] **Step 3: Add the minimal color helper**

Add above `main()` in `pc_postprocessing/visualize_pc.py`:

```python
def compute_point_colors(pc_data, cmap_name="viridis"):
    initial_heights = pc_data[0, :, :, 2]
    min_heights = initial_heights.min(axis=1, keepdims=True)
    height_ranges = np.ptp(initial_heights, axis=1, keepdims=True)
    normalized_heights = np.full(initial_heights.shape, 0.5, dtype=np.float64)
    np.divide(
        initial_heights - min_heights,
        height_ranges,
        out=normalized_heights,
        where=height_ranges > 0,
    )
    return plt.get_cmap(cmap_name)(normalized_heights)
```

- [ ] **Step 4: Run the focused tests and verify both behaviors pass**

Run:

```bash
MPLCONFIGDIR=/tmp/matplotlib /Users/jaysonlin/miniconda3/envs/pc_env/bin/python -m unittest test.test_pc_postprocessing -v
```

Expected: two tests run and report `OK`.

- [ ] **Step 5: Add the output option, precomputed colors, and shared colorbar**

Add the parser option and construct the output path from it:

```python
parser.add_argument(
    "--output_filename",
    type=str,
    default="pc_trajectory.mp4",
    help="Video filename written inside the sample directory",
)

# Later, after the figure and axes are created:
output_video_path = os.path.join(sample_dir, args.output_filename)
```

Replace the static object-color list with one precomputation and a shared colorbar:

```python
point_colors = compute_point_colors(pc_data)
colorbar_mappable = plt.cm.ScalarMappable(
    norm=plt.Normalize(vmin=0.0, vmax=1.0),
    cmap="viridis",
)
colorbar_mappable.set_array([])
colorbar = fig.colorbar(colorbar_mappable, ax=ax, pad=0.1, shrink=0.7)
colorbar.set_label("Relative initial height")
```

Pass the precomputed per-point colors to each scatter call:

```python
ax.scatter(
    pts[:, 0],
    pts[:, 1],
    pts[:, 2],
    c=point_colors[o_idx],
    s=4,
    alpha=0.8,
    edgecolors="none",
    label=f"Object {o_idx} (Instance {o_idx})",
)
```

- [ ] **Step 6: Run unit tests and syntax validation**

Run:

```bash
MPLCONFIGDIR=/tmp/matplotlib /Users/jaysonlin/miniconda3/envs/pc_env/bin/python -m unittest test.test_pc_postprocessing -v
/Users/jaysonlin/miniconda3/envs/pc_env/bin/python -m py_compile pc_postprocessing/visualize_pc.py test/test_pc_postprocessing.py
```

Expected: two tests report `OK`; compilation exits with status 0 and no output.

- [ ] **Step 7: Commit the tested implementation**

```bash
git add pc_postprocessing/visualize_pc.py test/test_pc_postprocessing.py
git commit -m "Add stable colormap to point cloud visualization"
```

### Task 2: Render and Verify `datasets/2_sample_1`

**Files:**
- Create: `datasets/2_sample_1/pc_trajectory_colormap.mp4` (generated preview, not committed)
- Verify unchanged: `datasets/2_sample_1/pc_trajectory.mp4`

**Interfaces:**
- Consumes: `datasets/2_sample_1/pc.hdf5` shaped `(24, 2, 2048, 3)` and the Task 1 CLI option.
- Produces: a 12 FPS, 24-frame `datasets/2_sample_1/pc_trajectory_colormap.mp4`.

- [ ] **Step 1: Record the original video's checksum and size**

Run:

```bash
shasum -a 256 datasets/2_sample_1/pc_trajectory.mp4
stat -f "%z bytes" datasets/2_sample_1/pc_trajectory.mp4
```

Expected: both commands succeed; retain the checksum for Step 4.

- [ ] **Step 2: Render only the requested dataset to the separate filename**

Run:

```bash
MPLCONFIGDIR=/tmp/matplotlib /Users/jaysonlin/miniconda3/envs/pc_env/bin/python pc_postprocessing/visualize_pc.py --sample_dir datasets/2_sample_1 --output_filename pc_trajectory_colormap.mp4
```

Expected: the log reports 24 rendered frames and success at `datasets/2_sample_1/pc_trajectory_colormap.mp4`.

- [ ] **Step 3: Verify the generated video's metadata and frame count**

Run:

```bash
/Users/jaysonlin/miniconda3/envs/pc_env/bin/python - <<'PY'
import os
import imageio.v2 as imageio

path = "datasets/2_sample_1/pc_trajectory_colormap.mp4"
reader = imageio.get_reader(path)
metadata = reader.get_meta_data()
frame_count = reader.count_frames()
reader.close()

assert os.path.getsize(path) > 0
assert frame_count == 24, frame_count
assert round(metadata["fps"]) == 12, metadata["fps"]
print({"bytes": os.path.getsize(path), "frames": frame_count, "fps": metadata["fps"]})
PY
```

Expected: a nonzero byte count, `frames: 24`, and `fps: 12.0`.

- [ ] **Step 4: Confirm the original video is unchanged**

Run:

```bash
shasum -a 256 datasets/2_sample_1/pc_trajectory.mp4
```

Expected: the checksum exactly matches the value recorded in Step 1.

- [ ] **Step 5: Inspect representative frames without creating a preview deliverable**

Extract frames 0, 12, and 23 outside the repository:

```bash
/Users/jaysonlin/miniconda3/envs/pc_env/bin/python - <<'PY'
import imageio.v2 as imageio

reader = imageio.get_reader("datasets/2_sample_1/pc_trajectory_colormap.mp4")
for frame_index in (0, 12, 23):
    imageio.imwrite(
        f"/tmp/pc_colormap_frame_{frame_index}.png",
        reader.get_data(frame_index),
    )
reader.close()
PY
```

Inspect `/tmp/pc_colormap_frame_0.png`, `/tmp/pc_colormap_frame_12.png`, and `/tmp/pc_colormap_frame_23.png` with the workspace image viewer. Confirm that both objects use non-uniform `viridis` colors, the colorbar reads `Relative initial height`, and the color assignment remains attached to corresponding surface regions through the sequence. The temporary files remain outside the repository and are not deliverables.

- [ ] **Step 6: Review the final worktree scope**

Run:

```bash
git status --short
git diff --check
git log -3 --oneline
```

Expected: only the user's pre-existing untracked files and the ignored/generated preview video remain outside commits; `git diff --check` is silent; the implementation and plan/spec commits appear in history.
