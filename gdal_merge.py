import os
import subprocess
import time


def merge_esa_worldcover(input_dir, output_path):
    """拼接ESA WorldCover数据中的Map.tif文件"""
    # 检查输入路径是否存在
    if not os.path.exists(input_dir):
        print(f"错误：输入路径不存在！{input_dir}")
        return False

    # 检查输出路径是否包含.tif后缀
    if not output_path.lower().endswith('.tif'):
        print(f"错误：输出路径必须包含.tif扩展名！当前路径：{output_path}")
        return False

    # 创建输出文件夹（如果不存在）
    output_dir = os.path.dirname(output_path)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"已创建输出文件夹：{output_dir}")

    # 收集所有Map.tif文件
    tif_files = []
    for root, dirs, files in os.walk(input_dir):
        for file in files:
            if file.endswith("Map.tif"):
                tif_files.append(os.path.join(root, file))

    if not tif_files:
        print("错误：未找到任何Map.tif文件！")
        return False

    print(f"找到 {len(tif_files)} 个文件，开始拼接...")

    # 记录开始时间
    start_time = time.time()

    # 构建GDAL命令（使用绝对路径指向Python和gdal_merge.py）
    python_exe = r"D:\Anaconda\envs\gis_final\python.exe"
    gdal_merge = r"D:\Anaconda\envs\gis_final\Scripts\gdal_merge.py"
    command = [
                  python_exe, gdal_merge,
                  "-o", output_path,
                  "-of", "GTiff",  # 输出格式
                  "-n", "0",  # 输入NoData值
                  "-a_nodata", "255"  # 输出NoData值
              ] + tif_files

    # 执行命令
    print("执行命令：", " ".join(command))
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )
        elapsed_time = time.time() - start_time
        print(f"✅ 拼接成功！耗时：{elapsed_time:.2f}秒")
        print(f"输出文件：{output_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 拼接失败！错误代码：{e.returncode}")
        print(f"错误信息：{e.stderr}")
        return False
    except Exception as e:
        print(f"❌ 执行异常：{str(e)}")
        return False


if __name__ == "__main__":
    print("=== ESA WorldCover数据拼接工具 ===")
    input_dir = input("请输入包含Map.tif文件的根目录路径（例如：E:\\data\\ESA_WorldCover）：")
    output_path = input("请输入输出拼接文件的完整路径（例如：E:\\output\\merged_result.tif）：")
    merge_esa_worldcover(input_dir, output_path)#成功拼接，还得是你