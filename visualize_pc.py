import os
import sys
import h5py
import numpy as np
import matplotlib.pyplot as plt
import imageio

def main():
    hdf5_path = "output/pc.hdf5"
    if not os.path.exists(hdf5_path):
        print(f"Error: {hdf5_path} not found. Please run generate_pc.py first.")
        sys.exit(1)

    print(f"Loading point clouds from {hdf5_path}...")
    with h5py.File(hdf5_path, "r") as f:
        pc_data = f["point_cloud"][:]  # (Frames, Objects, 2048, 3)

    num_frames, num_objects, num_points, _ = pc_data.shape
    print(f"Loaded point cloud sequence: {num_frames} frames, {num_objects} objects, {num_points} points per object.")

    # Calculate global axis limits to prevent auto-scaling jitter
    flat_pc = pc_data.reshape(-1, 3)
    min_coords = flat_pc.min(axis=0)
    max_coords = flat_pc.max(axis=0)
    padding = 0.5
    x_lim = (min_coords[0] - padding, max_coords[0] + padding)
    y_lim = (min_coords[1] - padding, max_coords[1] + padding)
    z_lim = (min_coords[2] - padding, max_coords[2] + padding)

    # Set up matplotlib figure
    fig = plt.figure(figsize=(10, 10))
    ax = fig.add_subplot(111, projection='3d')

    output_video_path = "output/pc_trajectory.mp4"
    print(f"Rendering frames and writing to {output_video_path}...")
    
    # We use imageio's mp4 writer (which downloads ffmpeg automatically if not present)
    writer = imageio.get_writer(output_video_path, fps=12)

    # Define color scheme for objects (first is yellow, second is blue, etc. to match Blender/CLEVR alignment)
    colors = ['#FFD700', '#1E90FF', '#3CB371', '#FF6347', '#9370DB', '#FF69B4']

    for f_idx in range(num_frames):
        ax.clear()
        
        # Set bounds and styling
        ax.set_xlim(x_lim)
        ax.set_ylim(y_lim)
        ax.set_zlim(z_lim)
        ax.set_xlabel("X")
        ax.set_ylabel("Y")
        ax.set_zlabel("Z")
        ax.set_title(f"Point Cloud Trajectories - Frame {f_idx:03d} / {num_frames-1:03d}", fontsize=14)
        
        # Draw grid and background styling
        ax.grid(True)
        
        # Plot each object
        for o_idx in range(num_objects):
            pts = pc_data[f_idx, o_idx, :, :]
            ax.scatter(pts[:, 0], pts[:, 1], pts[:, 2], 
                       c=colors[o_idx % len(colors)], 
                       s=4, 
                       alpha=0.8,
                       edgecolors='none',
                       label=f"Object {o_idx} (Instance {o_idx})")
            
        ax.legend(loc="upper right")

        # Convert matplotlib canvas to RGB numpy array
        fig.canvas.draw()
        rgba = fig.canvas.buffer_rgba()
        frame_img = np.asarray(rgba)[:, :, :3]
        
        writer.append_data(frame_img)
        print(f"  Rendered frame {f_idx + 1}/{num_frames}", end="\r")
        
    writer.close()
    plt.close(fig)
    print(f"\nVideo successfully saved to {output_video_path}")

if __name__ == "__main__":
    main()
