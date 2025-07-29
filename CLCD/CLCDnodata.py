import os
import logging
from tqdm import tqdm
from multiprocessing import Pool

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('tif_nodata_update.log'),
        logging.StreamHandler()
    ]
)


def set_nodata_value(args):
    """
    修改单个TIFF文件的NoData值（直接修改原文件）
    参数：
        args: 包含(tif_path, nodata)的元组
    """
    tif_path, nodata = args
    try:
        # 使用gdal_edit.py直接修改原文件
        cmd = f'gdal_edit.py -a_nodata {nodata} "{tif_path}"'
        exit_code = os.system(cmd)

        if exit_code == 0:
            logging.info(f'成功: {tif_path}')
            return True
        else:
            logging.error(f'失败[代码{exit_code}]: {tif_path}')
            return False

    except Exception as e:
        logging.error(f'异常: {tif_path} - {str(e)}')
        return False


def batch_process(folder_path, nodata=0, num_workers=4):
    """
    批量处理文件夹中的所有TIFF文件
    参数：
        folder_path: 包含TIFF的文件夹路径
        nodata: 要设置的NoData值
        num_workers: 并行处理的进程数
    """
    # 获取所有TIFF文件
    tif_files = []
    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith(('.tif', '.tiff')):
                tif_files.append(os.path.join(root, file))

    if not tif_files:
        logging.warning('未发现TIFF文件！')
        return

    logging.info(f'开始处理 {len(tif_files)} 个文件...')

    # 准备参数列表
    task_args = [(f, nodata) for f in tif_files]

    # 并行处理（带进度条）
    with Pool(processes=num_workers) as pool:
        results = list(tqdm(
            pool.imap(set_nodata_value, task_args),
            total=len(tif_files),
            desc='处理进度',
            unit='文件'
        ))

    # 统计结果
    success_count = sum(results)
    logging.info(
        f'处理完成！成功: {success_count}/{len(tif_files)} '
        f'({success_count / len(tif_files):.1%})'
    )


if __name__ == '__main__':
    # 使用示例
    input_folder = r'E:\GEOdata\LUCC\CLCD\CLCD_Full_Exports'  # 替换为你的TIFF文件夹路径

    # 参数配置
    config = {
        'nodata': 0,  # CLCD数据的无效值通常为0
        'num_workers': 6  # 根据CPU核心数调整
    }

    # 执行处理
    batch_process(input_folder, **config)
#成功运行,但是还是有黑色背景
