import struct
import json
import os

def parse_glb(file_path):
    with open(file_path, 'rb') as f:
        # Check magic
        magic = f.read(4)
        if magic != b'glTF':
            print("Not a GLB file")
            return
        
        version = struct.unpack('<I', f.read(4))[0]
        length = struct.unpack('<I', f.read(4))[0]
        
        print(f"GLB Version: {version}, Total Length: {length}")
        
        # Read chunks
        while f.tell() < length:
            chunk_length = struct.unpack('<I', f.read(4))[0]
            chunk_type = f.read(4)
            
            if chunk_type == b'JSON':
                json_data = f.read(chunk_length)
                data = json.loads(json_data)
                print_hierarchy(data)
                break
            else:
                # Skip other chunks
                f.read(chunk_length)

def print_hierarchy(data):
    print("\n--- Model Hierarchy ---")
    nodes = data.get('nodes', [])
    meshes = data.get('meshes', [])
    
    def print_node(node_index, indent=0):
        node = nodes[node_index]
        name = node.get('name', f"Node_{node_index}")
        mesh_idx = node.get('mesh')
        mesh_info = ""
        if mesh_idx is not None:
            mesh_name = meshes[mesh_idx].get('name', f"Mesh_{mesh_idx}")
            mesh_info = f" [Mesh: {mesh_name}]"
            
        trans = node.get('translation', [0, 0, 0])
        rot = node.get('rotation', [0, 0, 0, 1]) # x, y, z, w
        scale = node.get('scale', [1, 1, 1])
        
        # Format floats
        trans_str = f"[{', '.join(f'{x:.4f}' for x in trans)}]"
        rot_str = f"[{', '.join(f'{x:.4f}' for x in rot)}]"
        
        print("  " * indent + f"- {name}{mesh_info}")
        print("  " * indent + f"  Pos: {trans_str}, Rot: {rot_str}")

        
        children = node.get('children', [])
        for child_idx in children:
            print_node(child_idx, indent + 1)
            
    scenes = data.get('scenes', [])
    if scenes:
        root_nodes = scenes[data.get('scene', 0)].get('nodes', [])
        for root in root_nodes:
            print_node(root)
    else:
        print("No scenes found")

if __name__ == '__main__':
    file_path = r"c:\Users\聂\Documents\GitHub\zero-robotic-arm\robot-control-system\frontend\public\models\robot-arm.glb"
    if os.path.exists(file_path):
        parse_glb(file_path)
    else:
        print(f"File not found: {file_path}")
