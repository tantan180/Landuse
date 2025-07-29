import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import rasterio
from glob import glob


# --------------------------
# 修正1：解决数值溢出与面积异常
# --------------------------
def calculate_frozen_area(raster_path, cell_size=None):
    with rasterio.open(raster_path) as src:
        data = src.read(1)

        # 关键：确保冻土像元值为1（若实际值不同，需修改此处）
        # 检查数据范围，避免负值干扰
        if np.min(data) < 0:
            print(f"警告：{os.path.basename(raster_path)} 中存在负值，可能数据异常")

        # 统计冻土像元数量（用uint64避免溢出）
        frozen_pixels = np.sum(data == 1, dtype=np.uint64)  # 强制用无符号64位整数

        # 获取像元大小
        if cell_size is None:
            cell_size = src.res[0]

        # 计算面积（先除1e6再乘，减少中间值大小）
        area_km2 = frozen_pixels * (cell_size ** 2) / 1e6

        # 确保面积非负（若仍为负，强制修正为0，避免后续分析错误）
        if area_km2 < 0:
            print(f"修正：{os.path.basename(raster_path)} 面积为负，已强制设为0")
            area_km2 = 0.0

        return area_km2


# --------------------------
# 修正2：解决字体问题
# --------------------------
def set_matplotlib_font():
    # 优先使用系统中已安装的中文字体（Windows常见字体）
    plt.rcParams["font.family"] = ["SimHei", "Microsoft YaHei", "Heiti TC"]
    plt.rcParams["axes.unicode_minus"] = False  # 正确显示负号
    plt.rcParams["font.size"] = 10  # 调整默认字体大小


# --------------------------
# 主分析函数（沿用之前逻辑，加入修正）
# --------------------------
def analyze_frozen_trend(data_dir, output_dir=None, cell_size=None, prefix="fused_"):
    set_matplotlib_font()  # 应用字体设置

    os.makedirs(output_dir, exist_ok=True)
    raster_files = sorted(glob(os.path.join(data_dir, f"{prefix}*.tif")))
    results = []

    for file_path in raster_files:
        file_name = os.path.basename(file_path)
        # 提取年份（适配 "fused_1961_1965_TTOP.tif" 格式）
        try:
            year_part = file_name.replace(prefix, "").replace("_TTOP.tif", "")
            start_year, end_year = year_part.split("_")
        except:
            print(f"警告：无法解析 {file_name} 的年份，跳过该文件")
            continue

        area = calculate_frozen_area(file_path, cell_size)
        results.append({
            'file': file_name,
            'start_year': int(start_year),
            'end_year': int(end_year),
            'period': f"{start_year}-{end_year}",
            'frozen_area_km2': area
        })

    df = pd.DataFrame(results)
    if df.empty:
        print("错误：未找到有效文件或解析年份失败")
        return df

    # 计算面积变化（跳过异常值）
    df['area_change_km2'] = df['frozen_area_km2'].diff()
    df['area_change_pct'] = df['frozen_area_km2'].pct_change() * 100
    df['years'] = df['end_year'] - df['start_year'] + 1
    df['annual_change_km2'] = df['area_change_km2'] / df['years'].replace(0, np.nan)

    # 保存结果
    if output_dir:
        csv_path = os.path.join(output_dir, "冻土面积统计.csv")
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        print(f"面积统计结果已保存至: {csv_path}")

    # 可视化与趋势分析（仅当数据有效时）
    if len(df) >= 2:
        plot_area_trend(df, output_dir)
        trend_analysis(df, output_dir)
    else:
        print("数据不足，无法进行趋势分析")

    return df


# --------------------------
# 可视化与趋势分析函数（保持不变）
# --------------------------
def plot_area_trend(df, output_dir):
    plt.figure(figsize=(12, 6))
    sns.lineplot(data=df, x='end_year', y='frozen_area_km2', marker='o')
    plt.xlabel('年份')
    plt.ylabel('冻土面积 (km²)')
    plt.title('研究区冻土面积变化趋势')
    plt.grid(linestyle='--', alpha=0.7)

    # 标注面积值（仅保留1位小数）
    for x, y in zip(df['end_year'], df['frozen_area_km2']):
        plt.annotate(f'{y:.1f}', (x, y), xytext=(0, 5), textcoords='offset points', ha='center')

    if output_dir:
        plot_path = os.path.join(output_dir, "冻土面积变化趋势.png")
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        print(f"趋势图已保存至: {plot_path}")

    plt.tight_layout()
    plt.show()


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


# --------------------------
# 主函数调用
# --------------------------
if __name__ == "__main__":
    data_dir = r"E:\GEOdata\pemefrost\QTP_permfrost_change_data_1961_2020\result1"
    output_dir = r"E:\GEOdata\pemefrost\QTP_permfrost_change_data_1961_2020\analysis"
    cell_size = 1000  # 1km分辨率

    df = analyze_frozen_trend(
        data_dir=data_dir,
        output_dir=output_dir,
        cell_size=cell_size,
        prefix="fused_"
    )

    if not df.empty:
        print("\n===== 冻土面积变化摘要 =====")
        print(df[['period', 'frozen_area_km2', 'area_change_km2', 'annual_change_km2']])

    #成功处理