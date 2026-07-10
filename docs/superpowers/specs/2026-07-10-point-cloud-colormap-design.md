# Point Cloud Colormap Preview Design

## Goal

Replace the solid per-object point-cloud color with a stable, per-point colormap that makes surface geometry easier to read. Render the result only for `output/sample_0` so it can be evaluated before processing other samples.

## Color Mapping

- For each object, take every tracked point's Z coordinate from frame 0.
- Normalize those values to the range 0–1 independently per object.
- Map the normalized values through Matplotlib's perceptually uniform `viridis` colormap.
- Compute colors once and reuse them in every frame. Because point indices are tracked across the sequence, each color remains attached to the same surface point as the object moves and rotates.
- If an object's frame-0 Z values are constant, assign all its points the midpoint of the colormap to avoid division by zero.

Independent per-object normalization prioritizes visible geometry over absolute height comparisons between objects. A shared colorbar labeled `Relative initial height` communicates the normalized scale.

## Output and Scope

The visualizer will accept an output filename so the preview can be written to `output/sample_0/pc_trajectory_colormap.mp4`. The existing `pc_trajectory.mp4` remains untouched. No PNG preview will be generated.

Only the visualization step will run; the existing `output/sample_0/pc.hdf5` will be reused. No other sample will be generated or rendered.

## Code Structure

Color calculation will live in a small helper separate from the rendering loop. The loop will reuse the precomputed RGBA colors for each object rather than evaluating coordinates each frame. Existing axis bounds, camera view, labels, point size, alpha, grid, and frame rate remain unchanged.

## Verification

- Unit-test color normalization for ordinary and constant-height point clouds.
- Run the visualizer against `output/sample_0` with the preview output filename.
- Confirm that the output video exists, is non-empty, has the expected frame count, and leaves the original video unchanged.
- Inspect representative rendered frames extracted from the video for stable, non-uniform `viridis` coloring and a readable colorbar. These inspection frames are temporary verification artifacts, not deliverables.
