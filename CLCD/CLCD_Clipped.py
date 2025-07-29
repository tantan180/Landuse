import os
from osgeo import gdal
import multiprocessing
from tqdm import tqdm


def process_tif(args):
    """
    处理单个TIFF文件的核心函数
    :param args: (输入路径, 输出路径, 掩膜文件路径, nodata值)
    """
    input_path, output_path, mask_path, nodata = args

    try:
        # 使用gdalwarp进行精确裁剪（会真正删除边缘无效像素）
        cmd = f'gdalwarp -cutline "{mask_path}" -crop_to_cutline ' \
              f'-dstnodata {nodata} -co "COMPRESS=LZW" -co "TILED=YES" ' \
              f'"{input_path}" "{output_path}"'

        if os.system(cmd) == 0:
            return True, input_path
        else:
            return False, input_path
    except Exception as e:
        return False, f"{input_path} - {str(e)}"


def batch_clip(input_folder, output_folder, mask_shp, nodata=0, num_workers=4):
    """
    批量处理函数
    :param input_folder: 输入TIFF文件夹路径
    :param output_folder: 输出文件夹路径
    :param mask_shp: 裁剪用的矢量边界文件（.shp）
    :param nodata: 指定的NoData值（CLCD通常为0）
    :param num_workers: 并行进程数
    """
    # 创建输出目录
    os.makedirs(output_folder, exist_ok=True)

    # 获取所有TIFF文件
    tif_files = [f for f in os.listdir(input_folder)
                 if f.lower().endswith(('.tif', '.tiff'))]

    if not tif_files:
        print("未找到TIFF文件！")
        return

    print(f"开始处理 {len(tif_files)} 个文件...")

    # 准备任务参数
    task_args = [
        (
            os.path.join(input_folder, f),
            os.path.join(output_folder, f),
            mask_shp,
            nodata
        )
        for f in tif_files
    ]

    # 并行处理
    with multiprocessing.Pool(processes=num_workers) as pool:
        results = []
        for success, msg in tqdm(
                pool.imap(process_tif, task_args),
                total=len(tif_files),
                desc="处理进度",
                unit="文件"
        ):
            results.append((success, msg))

    # 打印统计结果
    success_count = sum(1 for r in results if r[0])
    print(f"\n处理完成！成功: {success_count}/{len(tif_files)}")

    # 记录失败文件
    failures = [r[1] for r in results if not r[0]]
    if failures:
        print("\n失败文件：")
        print("\n".join(failures))

        # 写入日志文件
        with open(os.path.join(output_folder, "processing_errors.log"), "w") as f:
            f.write("\n".join(failures))


if __name__ == "__main__":
    # 参数配置
    config = {
        "input_folder": r"E:\GEOdata\LUCC\CLCD\CLCD_Full_Exports",  # 原始TIFF文件夹
        "output_folder": r"E:\GEOdata\LUCC\CLCD\CLCD_CLIPPED",  # 输出文件夹
        "mask_shp": r"E:\\GEOdata\\LUCC\\1980-2023_1kmCNLUCC\\cjy_region_CNLUCC.shp",  # 裁剪边界矢量文件
        "nodata": 0,  # CLCD的无效值
        "num_workers": 6  # 并行进程数（建议不超过CPU核心数）
    }

    # 执行处理
    batch_clip(**config)