import os
import hashlib
import sys
import argparse
# import send2trash  # 移除未安装的模块依赖

def chunk_reader(fobj, chunk_size=1024):
    """Generator that reads a file in chunks of bytes"""
    while True:
        chunk = fobj.read(chunk_size)
        if not chunk:
            return
        yield chunk

def get_hash(filename, first_chunk_only=False, hash_algo=hashlib.sha1):
    hashobj = hash_algo()
    try:
        with open(filename, 'rb') as file_object:
            if first_chunk_only:
                hashobj.update(file_object.read(1024))
            else:
                for chunk in chunk_reader(file_object):
                    hashobj.update(chunk)
        return hashobj.hexdigest()
    except (OSError, PermissionError):
        return None

def is_safe_path(path):
    """确保不删除系统关键目录下的文件"""
    path = os.path.abspath(path).lower()
    unsafe_prefixes = [
        os.path.join(os.environ.get('SystemRoot', 'C:\\Windows')).lower(),
        os.path.join(os.environ.get('ProgramFiles', 'C:\\Program Files')).lower(),
        os.path.join(os.environ.get('ProgramFiles(x86)', 'C:\\Program Files (x86)')).lower(),
        "c:\\windows",
        "c:\\program files",
        "c:\\programdata"
    ]
    
    for unsafe in unsafe_prefixes:
        if path.startswith(unsafe):
            return False
    return True

def check_for_duplicates(paths):
    hashes_by_size = {}
    hashes_on_1k = {}
    hashes_full = {}

    for path in paths:
        if not os.path.exists(path):
            print(f"警告: 路径不存在 - {path}")
            continue
            
        print(f"正在扫描目录: {path}")
        for dirpath, dirnames, filenames in os.walk(path):
            # 跳过隐藏文件夹和系统文件夹
            if any(part.startswith('.') for part in dirpath.split(os.sep)):
                continue
                
            for filename in filenames:
                full_path = os.path.join(dirpath, filename)
                try:
                    if os.path.islink(full_path):
                        continue

                    file_size = os.path.getsize(full_path)
                    
                    if file_size < 1: 
                        continue
                        
                    hashes_by_size.setdefault(file_size, []).append(full_path)
                except (OSError, PermissionError):
                    continue

    # 1k hash check
    for size, files in hashes_by_size.items():
        if len(files) < 2:
            continue

        for filename in files:
            small_hash = get_hash(filename, first_chunk_only=True)
            if small_hash:
                hashes_on_1k.setdefault(small_hash, []).append(filename)

    # Full hash check
    for small_hash, files in hashes_on_1k.items():
        if len(files) < 2:
            continue

        for filename in files:
            full_hash = get_hash(filename, first_chunk_only=False)
            if full_hash:
                hashes_full.setdefault(full_hash, []).append(filename)
    
    return {k: v for k, v in hashes_full.items() if len(v) > 1}

def delete_duplicates(duplicates, dry_run=False):
    total_deleted_size = 0
    deleted_count = 0
    
    for hash_val, files in duplicates.items():
        # 按创建时间排序，保留最早的（或者按路径长度，这里保留第一个发现的作为“原件”）
        # 也可以根据需求修改保留逻辑，例如保留文件名最短的
        files.sort(key=lambda x: os.path.getctime(x))
        original = files[0]
        copies = files[1:]
        
        print(f"\n保留原件: {original}")
        for copy in copies:
            if not is_safe_path(copy):
                print(f"  [跳过] 系统路径保护: {copy}")
                continue
                
            try:
                size = os.path.getsize(copy)
                if not dry_run:
                    os.remove(copy) # 物理删除
                    # 尝试放入回收站更安全，但需要额外库。这里响应用户“删”的指令，直接删除。
                    print(f"  [已删除] {copy}")
                else:
                    print(f"  [待删除] {copy}")
                
                total_deleted_size += size
                deleted_count += 1
            except Exception as e:
                print(f"  [删除失败] {copy} - {e}")

    return deleted_count, total_deleted_size

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="重复文件查找与清理工具")
    parser.add_argument("paths", nargs='*', help="要扫描的目录路径")
    parser.add_argument("--delete", action="store_true", help="自动删除重复文件（保留一份）")
    parser.add_argument("--dry-run", action="store_true", help="仅模拟删除，不实际执行")
    
    args = parser.parse_args()
    
    scan_paths = args.paths
    if not scan_paths:
        # 默认扫描当前用户的 Downloads 和 Temp 目录，这是产生垃圾和重复文件的重灾区且相对安全
        user_profile = os.environ.get('USERPROFILE')
        if user_profile:
            scan_paths = [
                os.path.join(user_profile, 'Downloads'),
                os.path.join(os.environ.get('TEMP'))
            ]
        else:
            print("未指定路径且无法获取用户目录。")
            sys.exit(1)

    print(f"目标路径: {scan_paths}")
    if args.delete:
        print("!!! 警告: 已启用自动删除模式 !!!")
    
    duplicates = check_for_duplicates(scan_paths)
    
    if not duplicates:
        print("未发现重复文件。")
    else:
        count, size = delete_duplicates(duplicates, dry_run=not args.delete)
        if args.delete:
            print(f"\n清理完成。共删除 {count} 个文件，释放 {size/1024/1024:.2f} MB 空间。")
        else:
            print(f"\n扫描完成。发现 {sum(len(v)-1 for v in duplicates.values())} 个可删除的重复文件，共 {size/1024/1024:.2f} MB。")
            print("使用 --delete 参数运行此脚本以执行删除。")
