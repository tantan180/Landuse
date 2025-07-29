import os
import subprocess
import time
import logging
from datetime import datetime


def setup_logging(output_dir):
    """配置日志记录"""
    log_file = os.path.join(output_dir, f"worldcover_process_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return log_file


def merge_esa_worldcover(input_dir, output_path):
    """拼接ESA WorldCover数据中的Map.tif文件"""
    logging.info(f"开始拼接处理，输入目录: {input_dir}")

    if not os.path.exists(input_dir):
        logging.error(f"输入路径不存在: {input_dir}")
        return False

    if not output_path.lower().endswith('.tif'):
        logging.error("输出路径必须包含.tif扩展名")
        return False

    output_dir = os.path.dirname(output_path)
    os.makedirs(output_dir, exist_ok=True)
    logging.info(f"输出目录已准备: {output_dir}")

    # 收集所有Map.tif文件
    tif_files = []
    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.endswith("Map.tif"):
                tif_files.append(os.path.join(root, file))

    if not tif_files:
        logging.error("未找到任何Map.tif文件！")
        return False

    logging.info(f"找到 {len(tif_files)} 个Map.tif文件")

    start_time = time.time()
    python_exe = r"D:\Anaconda\envs\gis_final\python.exe"
    gdal_merge = r"D:\Anaconda\envs\gis_final\Scripts\gdal_merge.py"

    command = [
                  python_exe, gdal_merge,
                  "-o", output_path,
                  "-of", "GTiff",
                  "-n", "0",
                  "-a_nodata", "255",
                  "-co", "COMPRESS=LZW",
                  "-co", "BIGTIFF=YES"
              ] + tif_files

    logging.info("执行命令: " + " ".join(command))

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )
        elapsed_time = time.time() - start_time
        logging.info(f"拼接成功！耗时: {elapsed_time:.2f}秒")
        logging.info(f"输出文件: {output_path}")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"拼接失败！错误代码: {e.returncode}")
        logging.error(f"错误信息: {e.stderr}")
        return False


def clip_with_vector(input_tif, output_path, vector_file):
    """使用矢量文件裁剪TIFF"""
    logging.info(f"开始裁剪处理，输入文件: {input_tif}")

    if not all([os.path.exists(input_tif), os.path.exists(vector_file)]):
        logging.error("输入文件或矢量文件不存在！")
        return False

    start_time = time.time()
    command = [
        "gdalwarp",
        "-cutline", vector_file,
        "-crop_to_cutline",
        "-dstnodata", "255",
        "-co", "COMPRESS=LZW",
        "-co", "BIGTIFF=YES",
        "-multi",
        "-wo", "NUM_THREADS=ALL_CPUS",
        input_tif,
        output_path
    ]

    logging.info("执行命令: " + " ".join(command))

    try:
        subprocess.run(command, check=True)
        elapsed_time = time.time() - start_time
        logging.info(f"裁剪成功！耗时: {elapsed_time:.2f}秒")
        logging.info(f"输出文件: {output_path}")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"裁剪失败: {e.stderr}")
        return False


def process_worldcover(input_dir, output_dir, vector_dir=None):
    """完整的WorldCover处理流程"""
    # 设置日志
    log_file = setup_logging(output_dir)
    logging.info(f"日志文件已创建: {log_file}")

    # 1. 拼接
    merged_file = os.path.join(output_dir, "merged_worldcover.tif")
    if not merge_esa_worldcover(input_dir, merged_file):
        return False

    # 2. 裁剪（如果提供了矢量目录）
    if vector_dir and os.path.exists(vector_dir):
        # 查找矢量文件（支持.shp或.gpkg）
        vector_files = []
        for root, _, files in os.walk(vector_dir):
            for file in files:
                if file.endswith(('.shp', '.gpkg')):
                    vector_files.append(os.path.join(root, file))

        if not vector_files:
            logging.warning("矢量目录中未找到.shp或.gpkg文件，跳过裁剪步骤")
            return True

        # 对每个矢量文件执行裁剪
        for i, vector_file in enumerate(vector_files, 1):
            clipped_file = os.path.join(output_dir, f"clipped_{i}.tif")
            if not clip_with_vector(merged_file, clipped_file, vector_file):
                logging.error(f"使用矢量文件 {vector_file} 裁剪失败")
                continue

    return True


if __name__ == "__main__":
    print("=== ESA WorldCover数据处理工具 ===")
    input_dir = input("请输入包含Map.tif文件的根目录路径: ").strip()
    output_dir = input("请输入输出目录路径: ").strip()
    vector_dir = input("请输入矢量文件目录路径（可选，直接回车跳过）: ").strip() or None

    if not os.path.exists(input_dir):
        print(f"错误：输入路径不存在！{input_dir}")
        exit(1)

    os.makedirs(output_dir, exist_ok=True)

    if process_worldcover(input_dir, output_dir, vector_dir):
        print("处理完成！请查看输出目录和日志文件。")
    else:
        print("处理过程中出现错误，请检查日志。")