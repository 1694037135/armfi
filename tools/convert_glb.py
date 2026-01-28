import trimesh
import numpy as np
import os
from xml.etree.ElementTree import Element, SubElement, tostring
import xml.dom.minidom

def create_mujoco_xml(glb_path, output_dir):
    # Load the GLB file
    scene = trimesh.load(glb_path)
    
    # Create output directories
    meshes_dir = os.path.join(output_dir, "meshes_new")
    os.makedirs(meshes_dir, exist_ok=True)
    
    # XML Root
    root = Element('mujoco', model="robot_arm_glb")
    
    # Default settings
    # Default settings
    compiler = SubElement(root, 'compiler', angle="radian", meshdir="meshes_new")
    
    # Defaults
    default = SubElement(root, 'default')
    
    # Visual default
    def_visual = SubElement(default, 'default', {"class": "visual"})
    SubElement(def_visual, 'geom', material="visual_mat", group="2", contype="0", conaffinity="0")
    
    # Collision default
    def_collision = SubElement(default, 'default', {"class": "collision"})
    SubElement(def_collision, 'geom', material="collision_mat", group="1")
    
    # Assets (Materials & Meshes)
    asset = SubElement(root, 'asset')
    SubElement(asset, 'material', name="visual_mat", rgba="0.7 0.7 0.7 1")
    SubElement(asset, 'material', name="collision_mat", rgba="1 0 0 0.5")
    
    # Worldbody
    worldbody = SubElement(root, 'worldbody')
    SubElement(worldbody, 'geom', name="floor", type="plane", size="0 0 0.25", material="visual_mat")
    SubElement(worldbody, 'light', directional="true", pos="0 0 3")
    
    # Data extraction
    graph = scene.graph
    geometry = scene.geometry
    
    # Helper to traverse hierarchy
    # GLB usually has a structure. We need to find the kinematic chain.
    # For simplicity, we'll try to follow the node names we saw earlier.
    
    # Node names mapping to links
    link_names = {
        'base': 'base_link',
        'link1.001': 'link1',
        'link2': 'link2', 
        'link3': 'link3',
        'link4': 'link4',
        'link5': 'link5',
        'link6': 'link6'
    }
    
    # We need to scale positions from mm to m if they are large
    scale_factor = 0.001
    
    # Check scaling based on base node bounds
    # (Simplified: assume mm if bounding box > 10)
    
    def process_node(node_name, parent_xml_element, current_transform=np.eye(4)):
        # Get local transform of this node relative to parent
        # trimesh graph stores local transforms
        
        # Note: trimesh graph structure handles transforms. 
        # But we want to extract the kinematic tree properly.
        
        # Let's verify if node exists in our target list
        target_name = None
        for key in link_names:
            if key in node_name: # Simple string matching
                target_name = link_names[key]
                break
        
        # Get transform from parent
        # This is tricky with trimesh graph as it's a directed graph.
        # We'll rely on the structure we saw: base -> link1 -> ...
        
        pass

    # Better approach: Iterate specifically through our known chain
    # We saw the hierarchy in inspect_glb. Let's hardcode the chain extraction for robust results.
    
    # Create a mapping from our link names to actual graph node names
    # We iterate over all nodes in the graph to find matches
    actual_node_map = {}
    
    print("Mapping GLB nodes to robot links...")
    all_nodes = list(scene.graph.nodes)
    
    for link_key in link_names.keys():
        # Find the node that best matches this link key
        # We look for nodes that contain the key string
        matches = [n for n in all_nodes if link_key in n]
        
        # Heuristic: prefer nodes that have geometry
        geom_matches = [n for n in matches if n in scene.graph.geometry_nodes]
        
        if geom_matches:
            # Pick the shortest name or just the first one?
            # Usually the one with geometry is what we want.
            # link1.001 is a geom match.
            actual_node_map[link_key] = geom_matches[0]
            print(f"  Mapped '{link_key}' -> '{geom_matches[0]}'")
        elif matches:
            actual_node_map[link_key] = matches[0]
            print(f"  Mapped '{link_key}' -> '{matches[0]}' (No geometry)")
        else:
            print(f"  Warning: Could not find node for '{link_key}'")

    chain = ['base', 'link1.001', 'link2', 'link3', 'link4', 'link5', 'link6']
    xml_bodies = { 
        'world': worldbody,
        'joint_names': [] 
    }
    
    # Keep track of the previous link's actual node to calculate relative transforms
    prev_actual_node = 'world'
    
    for i, node_name in enumerate(chain):
        # process this link
        actual_node = actual_node_map.get(node_name)
        
        if not actual_node:
            print(f"Skipping {node_name} (not found)")
            continue
            
        print(f"Processing {node_name} (Node: {actual_node})...")
        
        # 1. Extract Mesh
        geom_names = scene.graph.geometry_nodes.get(actual_node)
        mesh = None
        
        if geom_names:
             # Try to find valid geometry
             for g_name in geom_names:
                 if g_name in geometry:
                     mesh = geometry[g_name].copy()
                     break
                 # Fallback: fuzzy lookup if exact key missing
                 for k in geometry.keys():
                     if g_name in k or k in g_name:
                         mesh = geometry[k].copy()
                         break
                 if mesh: break
        
        if mesh:
             # Apply scale 0.001 (mm to m)
             mesh.apply_scale(scale_factor)
             
             # Save STL
             stl_filename = f"{link_names.get(node_name, node_name)}.STL"
             stl_path = os.path.join(meshes_dir, stl_filename)
             mesh.export(stl_path)
             print(f"  Saved {stl_filename}")
             
             # Add mesh asset to XML
             SubElement(asset, 'mesh', name=stl_filename, file=stl_filename)
        else:
             print(f"  Warning: No mesh found for {actual_node}")

        # 2. Extract Transform
        # Calculate transform from PREVIOUS link to CURRENT link
        
        pos = [0, 0, 0]
        mujoco_quat = "1 0 0 0"

        if i == 0:
            # Base Link
            # Usually we define base at world origin (0,0,0) or keep its local transform
            # Let's keep it at 0,0,0 for the root body
            # But if the base node has a transform relative to world in GLB, we should respect it?
            # Typically robot base is at 0,0,0.
            pass
            
            body = SubElement(worldbody, 'body', name=link_names.get(node_name), pos="0 0 0")
            xml_bodies[node_name] = body
            prev_actual_node = actual_node
            
        else:
            # Child Links
            # Get transform from prev_actual_node to actual_node
            try:
                matrix, _ = scene.graph.get(frame_to=actual_node, frame_from=prev_actual_node)
                
                # Apply scaling to translation
                pos = matrix[:3, 3] * scale_factor
                
                # Rotation
                from scipy.spatial.transform import Rotation
                r = Rotation.from_matrix(matrix[:3, :3])
                quat = r.as_quat() # x, y, z, w
                mujoco_quat = f"{quat[3]:.4f} {quat[0]:.4f} {quat[1]:.4f} {quat[2]:.4f}"
                pos_str = f"{pos[0]:.4f} {pos[1]:.4f} {pos[2]:.4f}"
                
                print(f"  Rel Pos: {pos_str}")
                
                # Create Body
                # Find parent body in XML
                # The parent in chain is chain[i-1]
                parent_link_name = chain[i-1]
                parent_body = xml_bodies.get(parent_link_name)
                
                if parent_body is not None:
                    body_name = link_names.get(node_name, node_name)
                    body = SubElement(parent_body, 'body', name=body_name, pos=pos_str, quat=mujoco_quat)
                    xml_bodies[node_name] = body
                    
                    # Add Joint
                    joint_name = f"joint_{i}"
                    SubElement(body, 'joint', name=joint_name, type="hinge", axis="0 0 1", range="-1.57 1.57")
                    
                    # Store joint name for actuator creation
                    xml_bodies['joint_names'].append(joint_name)
                    
                    # Add Geometry
                    if mesh:
                        # ... (existing geometry code)
                        SubElement(body, 'geom', {"class": "visual"}, type="mesh", mesh=stl_filename, material="visual_mat")
                        SubElement(body, 'geom', type="mesh", mesh=stl_filename, material="collision_mat", group="1")
                    else:
                        # ... (existing fallback code)
                        print(f"  Added fallback capsule for {body_name}")
                        SubElement(body, 'geom', {"class": "visual"}, type="capsule", fromto="0 0 0 0.1 0 0", size="0.02", material="visual_mat")
                        SubElement(body, 'geom', type="capsule", fromto="0 0 0 0.1 0 0", size="0.02", material="collision_mat", group="1")
                    
                    # Add End Effector Site to the last link
                    if node_name == 'link6':
                         print(f"  Adding ee_site to {body_name}")
                         SubElement(body, 'site', name="ee_site", pos="0 0 0", size="0.01", rgba="1 0 0 1")

                prev_actual_node = actual_node
                
            except Exception as e:
                print(f"  Error getting transform: {e}")

    # Add Actuators
    actuator = SubElement(root, 'actuator')
    for j_name in xml_bodies.get('joint_names', []):
        SubElement(actuator, 'motor', name=f"{j_name}_ctrl", joint=j_name, gear="1")
    
    # Add Contact Exclusions (Critical for stability!)
    contact = SubElement(root, 'contact')
    # Exclude base <-> link1
    SubElement(contact, 'exclude', body1='base_link', body2='link1')
    # Exclude link_i <-> link_{i+1}
    for k in range(1, 6):
        SubElement(contact, 'exclude', body1=f'link{k}', body2=f'link{k+1}')

    # Save XML
    xml_str = xml.dom.minidom.parseString(tostring(root)).toprettyxml(indent="  ")
    output_xml_path = os.path.join(output_dir, "robot_arm_glb.xml")
    with open(output_xml_path, "w") as f:
        f.write(xml_str)
    
    print(f"\nSuccessfully created MuJoCo XML: {output_xml_path}")

if __name__ == "__main__":
    # Detect current directory structure
    current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # Adjust paths based on project root assumption
    glb_path = os.path.join(current_dir, "robot-control-system", "frontend", "public", "models", "robot-arm.glb")
    output_dir = os.path.join(current_dir, "5. Deep_LR")
    
    if os.path.exists(glb_path):
        create_mujoco_xml(glb_path, output_dir)
    else:
        # Fallback for absolute paths if needed, or print error
        print(f"Error: Could not find GLB at {glb_path}")
