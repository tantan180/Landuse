import numpy as np
import rasterio
import os
import glob
from tqdm import tqdm


def reclassify_clcd(input_path, output_dir, year_pattern=None):
    """
    重分类多年CLCD土地利用数据

    参数:
    input_path: 输入文件路径或包含多个文件的目录
    output_dir: 输出目录
    year_pattern: 年份模式，用于识别文件名中的年份
    """

    # 定义重分类规则
    reclass_rules = {
        1: 10,  # 农田 -> 耕地
        2: 20,  # 森林 -> 林地
        3: 30,  # 灌木 -> 灌木
        4: 41,  # 草原 -> 高覆盖草地 (默认)
        5: 50,  # 水域 -> 水域和冰雪
        6: 50,  # 冰雪 -> 水域和冰雪
        7: 60,  # 裸地 -> 裸地
        8: 70,  # 不透水面 -> 人造地表
        9: 80  # 湿地 -> 湿地
    }

    # 获取输入文件列表
    if os.path.isdir(input_path):
        # 如果是目录，查找所有tif文件
        input_files = glob.glob(os.path.join(input_path, "*.tif"))
        # 也可以根据特定模式查找，如: "CLCD_*.tif"
    elif os.path.isfile(input_path):
        # 如果是单个文件
        input_files = [input_path]
    else:
        # 支持文件模式匹配
        input_files = glob.glob(input_path)

    if not input_files:
        print("未找到输入文件")
        return

    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)

    print(f"找到 {len(input_files)} 个文件进行处理")

    # 处理每个文件
    for input_file in tqdm(input_files, desc="处理CLCD数据"):
        try:
            # 提取文件名和年份信息
            filename = os.path.basename(input_file)

            # 从文件名中提取年份（如果文件名包含年份）
            if year_pattern and year_pattern in filename:
                # 根据实际文件名模式调整提取逻辑
                year = filename.split(year_pattern)[-1].split('.')[0][:4]
                output_filename = f"reclassified_{year}.tif"
            else:
                output_filename = f"reclassified_{filename}"

            output_file = os.path.join(output_dir, output_filename)

            with rasterio.open(input_file) as src:
                # 读取数据
                data = src.read(1)
                profile = src.profile.copy()

                # 创建输出数组
                output_data = np.zeros_like(data)

                # 应用重分类规则
                for original_value, new_value in reclass_rules.items():
                    output_data[data == original_value] = new_value

                # 更新元数据
                profile.update(
                    dtype=rasterio.uint8,
                    nodata=0,
                    compress='lzw'
                )

                # 写入输出文件
                with rasterio.open(output_file, 'w', **profile) as dst:
                    dst.write(output_data, 1)

        except Exception as e:
            print(f"处理文件 {input_file} 时出错: {str(e)}")
            continue

    print(f"所有文件处理完成，结果保存在: {output_dir}")


# 方法1：处理单个目录下的所有tif文件
def process_directory(input_dir, output_dir):
    """处理目录中的所有CLCD文件"""
    reclassify_clcd(input_dir, output_dir)


# 方法2：处理特定年份范围的文件
def process_years_range(base_dir, start_year, end_year, output_dir):
    """处理指定年份范围的CLCD文件"""
    input_files = []
    for year in range(start_year, end_year + 1):
        # 根据实际文件名模式调整
        pattern = os.path.join(base_dir, f"*{year}*.tif")
        year_files = glob.glob(pattern)
        input_files.extend(year_files)

    if input_files:
        reclassify_clcd(input_files, output_dir, year_pattern=str(start_year)[:2])
    else:
        print("未找到指定年份的文件")


# 方法3：处理文件列表
def process_file_list(file_list, output_dir):
    """处理指定的文件列表"""
    reclassify_clcd(file_list, output_dir)


# 使用示例
if __name__ == "__main__":
    # 示例1：处理整个目录
    input_directory = r"E:\\GEOdata\\LUCC\\CLCD\\CLCD_CLIPPED"  # 输入目录路径
    output_directory = r"E:\\GEOdata\\LUCC\\CLCD\\reclass"  # 输出目录路径
    process_directory(input_directory, output_directory)

    # 示例2：处理特定年份范围（1985-2020）
    # process_years_range("/path/to/CLCD/data", 1985, 2020, "/path/to/output")

    # 示例3：处理特定文件列表
    # file_list = [
    #     "/path/to/CLCD_1985.tif",
    #     "/path/to/CLCD_1990.tif",
    #     # ... 其他文件
    # ]
    # process_file_list(file_list, "/path/to/output")
    #成功！！