import os
os.add_dll_directory(r"D:\Anaconda\envs\gis_final\Library\bin")  # Python 3.8+ 专用
import shapely  # 现在应该能正常导入

import numpy as np
import rasterio
import psutil
import logging

from rasterio.mask import mask
from rasterio.windows import Window
from concurrent.futures import ThreadPoolExecutor
from scipy import stats
import geopandas as gpd
from datetime import datetime

# 初始化日志系统
logging.basicConfig(
    filename='../raster_merge.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger()

#dll



def calculate_optimal_chunk(tiff_files, safety_factor=0.6):
    """动态计算分块大小（增强内存估算）"""
    mem = psutil.virtual_memory()
    available_mem_mb = mem.available / (1024 ** 2)

    with rasterio.open(tiff_files[0]) as src:
        dtype_size = np.dtype(src.dtypes[0]).itemsize
        # 根据波段数调整缓冲系数
        meta_buffer = 2.2 if src.count > 1 else 1.8

    chunk_size = int(np.sqrt(
        (available_mem_mb * 1024 ** 2 * safety_factor) /
        (len(tiff_files) * dtype_size * meta_buffer)
    ))

    # 限制在合理范围
    chunk_size = max(256, min(chunk_size, 4096))
    estimated_mem = (chunk_size ** 2 * len(tiff_files) * dtype_size) / (1024 ** 2)

    logger.info(
        f"内存计算 | 可用: {available_mem_mb:.1f}MB | "
        f"分块: {chunk_size}x{chunk_size} | "
        f"预估占用: {estimated_mem:.1f}MB"
    )
    return chunk_size, estimated_mem


def process_window(files, window, nodata):
    """带错误处理的并行窗口处理"""

    def read_block(f):
        try:
            with rasterio.open(f) as src:
                data = src.read(1, window=window, masked=True)
                return data.filled(src.nodata if src.nodata is not None else nodata)
        except Exception as e:
            logger.error(f"文件 {os.path.basename(f)} 读取失败: {str(e)}")
            return None

    try:
        with ThreadPoolExecutor(max_workers=min(8, len(files), os.cpu_count() or 4)) as executor:
            chunk_data = [x for x in executor.map(read_block, files) if x is not None]

        if not chunk_data:
            raise ValueError("所有文件读取失败")

        stacked = np.stack(chunk_data)
        if np.all(stacked == stacked[0, 0, 0]):
            return np.full(stacked.shape[1:], stacked[0, 0, 0], dtype=np.uint8)

        merged, _ = stats.mode(stacked, axis=0, keepdims=True)
        return merged.squeeze(0).astype(np.uint8)
    except Exception as e:
        logger.error(f"窗口处理失败: {str(e)}")
        raise


def memory_safe_merge(input_folder, output_path, boundary_shp=None):
    """完整的内存安全合并流程"""
    start_time = datetime.now()
    logger.info(f"开始处理: {input_folder}")

    # 1. 收集文件
    tiff_files = []
    for root, _, files in os.walk(input_folder):
        for f in files:
            if f.endswith('.tif') and '_Map.tif' in f:
                tiff_files.append(os.path.join(root, f))

    if not tiff_files:
        logger.error("未找到有效的分类图文件")
        raise ValueError("未找到有效的ESA分类图文件")

    logger.info(f"找到 {len(tiff_files)} 个分类图文件")

    # 2. 获取元数据
    with rasterio.open(tiff_files[0]) as src:
        meta = src.meta.copy()
        height, width = src.height, src.width
        dtype = np.uint8  # ESA数据强制转为uint8节省空间
        nodata = getattr(src, 'nodata', 255)

    # 3. 初始化输出
    meta.update({
        'count': 1,
        'dtype': dtype,
        'nodata': nodata,
        'compress': 'lzw',
        'tiled': True,
        'blockxsize': 256,
        'blockysize': 256,
        'driver': 'GTiff'
    })

    # 4. 分块处理
    chunk_size, _ = calculate_optimal_chunk(tiff_files)
    MIN_CHUNK, MAX_CHUNK = 256, 4096
    total_blocks = ((height // chunk_size) + 1) * ((width // chunk_size) + 1)
    processed_blocks = 0

    try:
        with rasterio.open(output_path, 'w', **meta) as dst:
            i = 0
            while i < height:
                j = 0
                while j < width:
                    # 动态调整
                    mem = psutil.virtual_memory()
                    if mem.percent > 85:
                        chunk_size = max(MIN_CHUNK, chunk_size // 2)
                        logger.warning(f"内存紧张({mem.percent}%)，分块调整为 {chunk_size}")

                    # 计算窗口
                    win_h = min(chunk_size, height - i)
                    win_w = min(chunk_size, width - j)
                    window = Window(j, i, win_w, win_h)

                    try:
                        # 处理并写入
                        merged_chunk = process_window(tiff_files, window, nodata)
                        dst.write(merged_chunk, 1, window=window)

                        # 进度显示
                        processed_blocks += 1
                        progress = processed_blocks / total_blocks
                        print(f"\r进度: {progress:.1%} | 内存: {mem.percent}% | 当前分块: {chunk_size}", end='')

                        # 动态调整分块
                        if mem.percent < 60 and chunk_size < MAX_CHUNK:
                            chunk_size = min(MAX_CHUNK, chunk_size * 2)

                        j += win_w
                    except Exception as e:
                        logger.error(f"窗口({i},{j})失败: {str(e)}")
                        chunk_size = max(MIN_CHUNK, chunk_size // 2)
                        if chunk_size <= MIN_CHUNK:
                            raise MemoryError("分块已降至最小值仍失败")

                i += chunk_size

        # 5. 验证输出
        with rasterio.open(output_path) as src:
            data = src.read(1)
            unique_vals = np.unique(data)
            logger.info(f"输出文件验证 - 唯一值: {unique_vals}")
            if len(unique_vals) == 1 and unique_vals[0] == nodata:
                logger.warning("输出文件可能全为NoData值!")

        # 6. 可选裁剪
        if boundary_shp:
            logger.info("开始裁剪操作...")
            with rasterio.open(output_path) as src:
                boundary = gpd.read_file(boundary_shp).to_crs(src.crs)
                out_image, out_transform = mask(
                    src, boundary.geometry, crop=True, all_touched=True, nodata=nodata
                )

                meta.update({
                    "height": out_image.shape[1],
                    "width": out_image.shape[2],
                    "transform": out_transform
                })

                clipped_path = output_path.replace('.tif', '_clipped.tif')
                with rasterio.open(clipped_path, 'w', **meta) as dst:
                    dst.write(out_image)
                logger.info(f"裁剪结果保存至: {clipped_path}")

        logger.info(f"处理完成! 耗时: {datetime.now() - start_time}")
        print(f"\n处理成功完成! 输出文件: {output_path}")

    except Exception as e:
        logger.critical(f"处理中断: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    try:
        input_folder = r"E:\GEOdata\LUCC\ESA_World_Cover\2020\terrascope_download_20250708_110802\WORLDCOVER\ESA_WORLDCOVER_10M_2020_V100\MAP"
        output_path = r"E:\GEOdata\LUCC\ESA_World_Cover\2020\merged_2020.tif"
        boundary_shp = r"E:\GEOdata\长江源\长江源区径流及土壤水分变化（2003-2018）\cjy_region_Buffer.shp"

        memory_safe_merge(input_folder, output_path, boundary_shp)

    except MemoryError as e:
        logger.error(f"内存不足: {e}")
        print(f"内存不足: {e}\n建议: 1) 使用更小分块 2) 物理内存扩容")
    except Exception as e:
        logger.error(f"主程序错误: {e}", exc_info=True)
        print(f"处理失败: {e}\n详细日志见 raster_merge.log")
    finally:
        logging.shutdown()