import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import rasterio
from glob import glob
from multiprocessing import Pool


# 设置字体
def set_matplotlib_font():
    plt.rcParams["font.family"] = ["SimHei", "Microsoft YaHei", "Heiti TC"]
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["font.size"] = 10


# 计算冻土面积
def calculate_frozen_area(raster_path):
    try:
        with rasterio.open(raster_path) as src:
            data = src.read(1)
            # 自动获取像元大小（根据栅格分辨率计算）
            cell_size = abs(src.transform[0] * src.transform[4])  # 获取每个像元的大小（单位：米）

            # 计算冻土像元数量
            frozen_pixels = np.sum(data == 1, dtype=np.uint64)

            # 计算冻土区的总面积（单位：平方千米）
            area_km2 = frozen_pixels * (cell_size ** 2) / 1e6

            # 修正面积为负的情况
            if area_km2 < 0:
                print(f"警告：{os.path.basename(raster_path)} 面积为负，已修正为0")
                area_km2 = 0.0
            return area_km2
    except Exception as e:
        print(f"错误：处理文件 {raster_path} 时发生错误: {e}")
        return np.nan


# 获取文件路径和时间范围
def get_time_range(file_name, prefix="fused_"):
    try:
        year_part = file_name.replace(prefix, "").replace("_TTOP.tif", "")
        start_year, end_year = year_part.split("_")
        return int(start_year), int(end_year), f"{start_year}-{end_year}"
    except:
        print(f"警告：无法解析 {file_name} 的年份，跳过该文件")
        return None, None, None


# 批量处理冻土栅格并分析面积
def analyze_frozen_trend(data_dir, output_dir=None, cell_size=None, prefix="fused_"):
    set_matplotlib_font()  # 设置字体

    os.makedirs(output_dir, exist_ok=True)
    raster_files = sorted(glob(os.path.join(data_dir, f"{prefix}*.tif")))
    results = []

    # 使用并行计算来提高效率
    with Pool(processes=4) as pool:  # 根据你的机器选择适合的进程数
        results = pool.map(process_raster, raster_files)

    # 创建DataFrame并处理结果
    df = pd.DataFrame(results)
    df = df.dropna(subset=['frozen_area_km2'])  # 删除面积为NaN的行
    df['area_change_km2'] = df['frozen_area_km2'].diff()
    df['area_change_pct'] = df['frozen_area_km2'].pct_change() * 100
    df['years'] = df['end_year'] - df['start_year'] + 1
    df['annual_change_km2'] = df['area_change_km2'] / df['years'].replace(0, np.nan)

    if output_dir:
        csv_path = os.path.join(output_dir, "冻土面积统计.csv")
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        print(f"面积统计结果已保存至: {csv_path}")

    if len(df) >= 2:
        plot_area_trend(df, output_dir)
        trend_analysis(df, output_dir)
    else:
        print("数据不足，无法进行趋势分析")

    return df


# 单个文件的处理函数
def process_raster(raster_path):
    file_name = os.path.basename(raster_path)
    start_year, end_year, period = get_time_range(file_name)

    if start_year is None or end_year is None:
        return None

    area = calculate_frozen_area(raster_path)

    return {
        'file': file_name,
        'start_year': start_year,
        'end_year': end_year,
        'period': period,
        'frozen_area_km2': area
    }


# 可视化函数：面积趋势
def plot_area_trend(df, output_dir):
    plt.figure(figsize=(12, 6))
    sns.lineplot(data=df, x='end_year', y='frozen_area_km2', marker='o')
    plt.xlabel('年份')
    plt.ylabel('冻土面积 (km²)')
    plt.title('研究区冻土面积变化趋势')
    plt.grid(linestyle='--', alpha=0.7)

    # 标注面积值（保留1位小数）
    for x, y in zip(df['end_year'], df['frozen_area_km2']):
        plt.annotate(f'{y:.1f}', (x, y), xytext=(0, 5), textcoords='offset points', ha='center')

    if output_dir:
        plot_path = os.path.join(output_dir, "冻土面积变化趋势.png")
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        print(f"趋势图已保存至: {plot_path}")

    plt.tight_layout()
    plt.show()


# 趋势分析
def trend_analysis(df, output_dir):
    x = df['end_year']
    y = df['frozen_area_km2']
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
    mean_area = np.mean(y)
    annual_change_pct = (slope / mean_area) * 100 if mean_area != 0 else 0

    print("\n===== 冻土面积变化趋势分析 =====")
    print(f"线性回归方程: y = {slope:.2f}x + {intercept:.2f}")
    print(f"相关系数 (R²): {r_value ** 2:.4f}")
    print(f"P值: {p_value:.4f}")
    print(f"年平均变化速率: {slope:.2f} km²/年")
    print(f"年平均变化率: {annual_change_pct:.2f}%/年")

    sig = "显著减少" if (slope < 0 and p_value < 0.05) else \
        "显著增加" if (slope > 0 and p_value < 0.05) else "不显著"
    print(f"趋势显著性: 冻土面积{sig} (P {'<' if p_value < 0.05 else '≥'} 0.05)")

    if output_dir:
        with open(os.path.join(output_dir, "冻土面积趋势分析.txt"), 'w', encoding='utf-8') as f:
            f.write(f"线性回归方程: y = {slope:.2f}x + {intercept:.2f}\n")
            f.write(f"R²: {r_value ** 2:.4f}, P值: {p_value:.4f}\n")
            f.write(f"年平均变化速率: {slope:.2f} km²/年\n")
            f.write(f"趋势显著性: {sig}\n")


if __name__ == "__main__":
    data_dir = r"E:\GEOdata\pemefrost\QTP_permfrost_change_data_1961_2020\result1"
    output_dir = r"E:\GEOdata\pemefrost\QTP_permfrost_change_data_1961_2020\analysis"
    df = analyze_frozen_trend(data_dir=data_dir, output_dir=output_dir, cell_size=None, prefix="fused_")
    if not df.empty:
        print("\n===== 冻土面积变化摘要 =====")
        print(df[['period', 'frozen_area_km2', 'area_change_km2', 'annual_change_km2']])
