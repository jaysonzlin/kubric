import sys
import os

conda_prefix = "/Users/jaysonlin/miniconda3/envs/pc_env"
if not os.path.exists(conda_prefix):
    conda_prefix = os.environ.get("CONDA_PREFIX")

if conda_prefix:
    lib_dir = os.path.join(conda_prefix, "lib")
    if os.path.exists(lib_dir):
        for py_dir in os.listdir(lib_dir):
            if py_dir.startswith("python"):
                site_packages = os.path.join(lib_dir, py_dir, "site-packages")
                if os.path.exists(site_packages) and site_packages not in sys.path:
                    sys.path.append(site_packages)

import json
import numpy as np
import bpy
import bmesh
import trimesh
import h5py

def farthest_point_sampling(pts, num_samples):
    """Greedy Farthest Point Sampling algorithm."""
    M = pts.shape[0]
    selected_indices = np.zeros(num_samples, dtype=np.int32)
    selected_indices[0] = 0
    distances = np.sum((pts - pts[0]) ** 2, axis=1)
    
    for i in range(1, num_samples):
        idx = np.argmax(distances)
        selected_indices[i] = idx
        new_distances = np.sum((pts - pts[idx]) ** 2, axis=1)
        distances = np.minimum(distances, new_distances)
        
    return selected_indices

def compute_barycentric_coordinates(pts, tri_verts):
    """Vectorized calculation of barycentric coordinates (u, v, w) for points on triangles."""
    a = tri_verts[:, 0, :]
    b = tri_verts[:, 1, :]
    c = tri_verts[:, 2, :]
    
    v0 = b - a
    v1 = c - a
    v2 = pts - a
    
    d00 = np.sum(v0 * v0, axis=1)
    d01 = np.sum(v0 * v1, axis=1)
    d11 = np.sum(v1 * v1, axis=1)
    d20 = np.sum(v2 * v0, axis=1)
    d21 = np.sum(v2 * v1, axis=1)
    
    denom = d00 * d11 - d01 * d01
    denom = np.where(denom == 0, 1e-10, denom)
    
    v = (d11 * d20 - d01 * d21) / denom
    w = (d00 * d21 - d01 * d20) / denom
    u = 1.0 - v - w
    
    return np.stack([u, v, w], axis=-1)

def main():
    # Load metadata.json
    metadata_path = "output/metadata.json"
    if not os.path.exists(metadata_path):
        print(f"Error: {metadata_path} not found.")
        sys.exit(1)
        
    with open(metadata_path, "r") as f:
        metadata = json.load(f)
        
    instances = metadata["instances"]
    flags = metadata["flags"]
    frame_start = flags["frame_start"]
    frame_end = flags["frame_end"]
    num_frames = frame_end - frame_start + 1
    num_objects = len(instances)
    
    print(f"Processing scene with {num_objects} objects over {num_frames} frames ({frame_start} to {frame_end})")
    
    # Collect all mesh objects that are foreground objects
    mesh_objs = []
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            if obj.name.lower() not in ["floor", "kubricobjectcoordinatesoverride"]:
                mesh_objs.append(obj)
                
    # Align the Blender mesh objects to instances in metadata using their position at the start frame
    bpy.context.scene.frame_set(frame_start)
    dg = bpy.context.evaluated_depsgraph_get()
    
    aligned_objs = []
    for inst_idx, inst in enumerate(instances):
        inst_pos = np.array(inst["positions"][0])
        best_obj = None
        min_dist = float("inf")
        for obj in mesh_objs:
            eval_obj = obj.evaluated_get(dg)
            obj_pos = np.array(eval_obj.matrix_world.translation)
            dist = np.linalg.norm(obj_pos - inst_pos)
            if dist < min_dist:
                min_dist = dist
                best_obj = obj
        aligned_objs.append(best_obj)
        print(f"Aligned: Instance {inst_idx} ({inst['asset_id']}) -> Blender Object: {best_obj.name}")
        
    # Extract local triangulated vertices and faces for each aligned object
    local_meshes = []
    for obj in aligned_objs:
        eval_obj = obj.evaluated_get(dg)
        mesh_data = eval_obj.to_mesh()
        
        bm = bmesh.new()
        bm.from_mesh(mesh_data)
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
        
        local_verts = np.array([v.co for v in bm.verts])
        faces = np.array([[v.index for v in f.verts] for f in bm.faces])
        
        bm.free()
        eval_obj.to_mesh_clear()
        local_meshes.append((local_verts, faces))
        
    # Sample point clouds and set up trackers
    object_trackers = []
    for o_idx in range(num_objects):
        obj = aligned_objs[o_idx]
        local_verts, faces = local_meshes[o_idx]
        
        # Get world vertices at start frame
        bpy.context.scene.frame_set(frame_start)
        dg = bpy.context.evaluated_depsgraph_get()
        eval_obj = obj.evaluated_get(dg)
        mwt = np.array(eval_obj.matrix_world)
        
        local_verts_hom = np.hstack([local_verts, np.ones((local_verts.shape[0], 1))])
        world_verts_start = (local_verts_hom @ mwt.T)[:, :3]
        
        # Sample points off the surface using trimesh
        mesh = trimesh.Trimesh(vertices=world_verts_start, faces=faces)
        pts, face_indices = trimesh.sample.sample_surface(mesh, 2048 * 20)
        
        # Select 2048 points using farthest point sampling
        selected_indices = farthest_point_sampling(pts, 2048)
        selected_pts = pts[selected_indices]
        selected_face_indices = face_indices[selected_indices]
        
        # Get triangle vertices and compute barycentric coordinates
        tri_vert_indices = faces[selected_face_indices]
        tri_verts = world_verts_start[tri_vert_indices]
        barycentric = compute_barycentric_coordinates(selected_pts, tri_verts)
        
        object_trackers.append({
            "local_verts": local_verts,
            "tri_vert_indices": tri_vert_indices,
            "barycentric": barycentric
        })
        
    # Reconstruct trajectories over all frames
    pc_data = np.zeros((num_frames, num_objects, 2048, 3), dtype=np.float32)
    
    for f_idx, frame in enumerate(range(frame_start, frame_end + 1)):
        bpy.context.scene.frame_set(frame)
        dg = bpy.context.evaluated_depsgraph_get()
        
        for o_idx in range(num_objects):
            obj = aligned_objs[o_idx]
            tracker = object_trackers[o_idx]
            
            eval_obj = obj.evaluated_get(dg)
            mwt = np.array(eval_obj.matrix_world)
            
            local_verts = tracker["local_verts"]
            local_verts_hom = np.hstack([local_verts, np.ones((local_verts.shape[0], 1))])
            world_verts_t = (local_verts_hom @ mwt.T)[:, :3]
            
            tri_vert_indices = tracker["tri_vert_indices"]
            tri_verts_t = world_verts_t[tri_vert_indices]
            
            barycentric = tracker["barycentric"]
            u = barycentric[:, 0, None]
            v = barycentric[:, 1, None]
            w = barycentric[:, 2, None]
            
            pts_t = u * tri_verts_t[:, 0, :] + v * tri_verts_t[:, 1, :] + w * tri_verts_t[:, 2, :]
            pc_data[f_idx, o_idx, :, :] = pts_t
            
    # Save the output to HDF5
    output_filepath = "output/pc.hdf5"
    with h5py.File(output_filepath, "w") as f:
        f.create_dataset("point_cloud", data=pc_data)
        
    print(f"Successfully generated point cloud trajectory dataset of shape {pc_data.shape} and saved to {output_filepath}")

if __name__ == "__main__":
    main()
