import glob
import os
import numpy as np
import pandas as pd
import rasterio
import matplotlib.pyplot as plt
from scipy import stats
from sklearn.linear_model import LinearRegression


def analyze_grassland_change(input_dir, output_dir):
    """
    分析草地类型变化
    """
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)

    # 初始化结果DataFrame
    results = pd.DataFrame(columns=['Year', 'Total_Grassland', 'High_Cover',
                                    'Medium_Cover', 'Low_Cover', 'High_Percent',
                                    'Medium_Percent', 'Low_Percent'])

    # 遍历所有年份文件夹
    years = []
    for year_dir in sorted(glob.glob(os.path.join(input_dir, "*"))):
        if os.path.isdir(year_dir):
            year = os.path.basename(year_dir)
            years.append(year)

            # 查找该年份的TIF文件（假设每个年份文件夹只有一个TIF）
            tif_files = glob.glob(os.path.join(year_dir, "*.tif"))
            if not tif_files:
                continue

            tif_file = tif_files[0]

            # 读取数据并计算各类草地面积
            with rasterio.open(tif_file) as src:
                data = src.read(1)
                transform = src.transform
                pixel_area = abs(transform.a * transform.e) / 1000000  # 单位: km²

                # 计算各类草地像元数
                high_cover = np.sum((data >= 31) & (data < 32))
                medium_cover = np.sum((data >= 32) & (data < 33))
                low_cover = np.sum((data >= 33) & (data < 34))
                total_grass = high_cover + medium_cover + low_cover

                # 计算面积(km²)
                high_area = high_cover * pixel_area
                medium_area = medium_cover * pixel_area
                low_area = low_cover * pixel_area
                total_area = total_grass * pixel_area

                # 计算比例
                if total_grass > 0:
                    high_percent = high_cover / total_grass * 100
                    medium_percent = medium_cover / total_grass * 100
                    low_percent = low_cover / total_grass * 100
                else:
                    high_percent = medium_percent = low_percent = 0

                # 添加到结果表
                results.loc[len(results)] = [
                    int(year), total_area, high_area, medium_area, low_area,
                    high_percent, medium_percent, low_percent
                ]

    # 保存结果到CSV
    results.to_csv(os.path.join(output_dir, 'grassland_change_results.csv'), index=False)

    # 分析趋势
    analyze_trends(results, output_dir)

    return results


def analyze_trends(df, output_dir):
    """
    进行趋势分析并绘制图表 - 优化版
    """
    try:
        # 设置绘图风格 - 从可用样式中选择最佳方案
        preferred_order = [
            'seaborn-v0_8',  # 最接近原始seaborn样式
            'seaborn-v0_8-darkgrid',  # 带灰色网格
            'ggplot',  # R语言ggplot2风格
            'fivethirtyeight',  # 538网站风格
            'bmh',  # Bayesian Methods for Hackers风格
            'default'  # 最后回退到默认
        ]

        # 选择第一个可用的样式
        selected_style = next((style for style in preferred_order
                               if style in plt.style.available), 'default')
        plt.style.use(selected_style)
        print(f"使用的绘图样式: {selected_style}")

        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)

        # 设置颜色方案（与样式独立）
        colors = {
            'High_Cover': '#2ca02c',  # 绿色
            'Medium_Cover': '#ff7f0e',  # 橙色
            'Low_Cover': '#d62728',  # 红色
            'Total': '#1f77b4'  # 蓝色
        }

        # 1. 草地总面积变化趋势
        plt.figure(figsize=(12, 6))
        ax = plt.gca()
        df.plot(x='Year', y='Total_Grassland', ax=ax,
                marker='o', linestyle='-', color=colors['Total'],
                linewidth=2, markersize=8, label='Total Grassland')

        plt.title('Total Grassland Area Change (1980-2023)', fontsize=14)
        plt.xlabel('Year', fontsize=12)
        plt.ylabel('Area (km²)', fontsize=12)
        plt.grid(True, linestyle='--', alpha=0.6)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, '1_total_grassland_trend.png'),
                    dpi=300, bbox_inches='tight')
        plt.close()

        # 2. 不同类型草地面积变化
        plt.figure(figsize=(12, 6))
        ax = plt.gca()

        df.plot(x='Year', y='High_Cover', ax=ax,
                marker='o', linestyle='-', color=colors['High_Cover'],
                linewidth=2, markersize=8, label='High Cover (31)')

        df.plot(x='Year', y='Medium_Cover', ax=ax,
                marker='s', linestyle='--', color=colors['Medium_Cover'],
                linewidth=2, markersize=8, label='Medium Cover (32)')

        df.plot(x='Year', y='Low_Cover', ax=ax,
                marker='^', linestyle='-.', color=colors['Low_Cover'],
                linewidth=2, markersize=8, label='Low Cover (33)')

        plt.title('Grassland Area Change by Cover Type (1980-2023)', fontsize=14)
        plt.xlabel('Year', fontsize=12)
        plt.ylabel('Area (km²)', fontsize=12)
        plt.legend(fontsize=10, framealpha=0.9)
        plt.grid(True, linestyle='--', alpha=0.6)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, '2_grassland_by_type_trend.png'),
                    dpi=300, bbox_inches='tight')
        plt.close()

        # 3. 不同类型草地比例变化（堆叠面积图）
        plt.figure(figsize=(12, 6))
        ax = plt.gca()

        # 计算堆叠数据
        df['Other_Percent'] = 100 - df[['High_Percent', 'Medium_Percent', 'Low_Percent']].sum(axis=1)

        ax.stackplot(df['Year'],
                     df['High_Percent'],
                     df['Medium_Percent'],
                     df['Low_Percent'],
                     df['Other_Percent'],
                     colors=[colors['High_Cover'],
                             colors['Medium_Cover'],
                             colors['Low_Cover'],
                             'lightgray'],
                     labels=['High Cover %', 'Medium Cover %', 'Low Cover %', 'Other %'],
                     alpha=0.8)

        plt.title('Grassland Composition Change (1980-2023)', fontsize=14)
        plt.xlabel('Year', fontsize=12)
        plt.ylabel('Percentage (%)', fontsize=12)
        plt.legend(loc='upper left', fontsize=10, framealpha=0.9)
        plt.grid(True, linestyle='--', alpha=0.6)
        plt.ylim(0, 100)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, '3_grassland_composition_stack.png'),
                    dpi=300, bbox_inches='tight')
        plt.close()

        # 4. 趋势显著性检验
        print("\n=== 趋势显著性检验(Mann-Kendall) ===")
        for col in ['Total_Grassland', 'High_Cover', 'Medium_Cover', 'Low_Cover']:
            tau, p_value = stats.kendalltau(df['Year'], df[col])
            trend = "↑ 显著上升" if tau > 0 and p_value < 0.05 else \
                "↓ 显著下降" if tau < 0 and p_value < 0.05 else \
                    "→ 无显著趋势"
            print(f"{col:15s}: tau={tau:+.3f}, p={p_value:.4f} {trend}")

        # 5. 变化速率计算
        print("\n=== 年均变化速率 ===")
        X = df['Year'].values.reshape(-1, 1)
        for col in ['Total_Grassland', 'High_Cover', 'Medium_Cover', 'Low_Cover']:
            model = LinearRegression().fit(X, df[col])
            change_rate = model.coef_[0]
            change_percent = change_rate / df[col].mean() * 100 if df[col].mean() != 0 else 0
            print(f"{col:15s}: {change_rate:+.2f} km²/年 | {change_percent:+.2f}%/年")

        # 6. 保存分析结果
        result_report = os.path.join(output_dir, 'analysis_report.txt')
        with open(result_report, 'w', encoding='utf-8') as f:
            f.write("草地变化分析报告\n")
            f.write("=" * 40 + "\n")
            f.write(f"分析时间: {pd.Timestamp.now()}\n\n")

            f.write("各年份草地面积数据:\n")
            df.to_string(f, index=False)
            f.write("\n\n")

            f.write("趋势检验结果:\n")
            for col in ['Total_Grassland', 'High_Cover', 'Medium_Cover', 'Low_Cover']:
                tau, p_value = stats.kendalltau(df['Year'], df[col])
                f.write(f"{col:15s}: tau={tau:+.3f}, p={p_value:.4f}\n")

            f.write("\n变化速率:\n")
            for col in ['Total_Grassland', 'High_Cover', 'Medium_Cover', 'Low_Cover']:
                model = LinearRegression().fit(X, df[col])
                # 使用km2代替km²避免编码问题
                change_rate = model.coef_[0]
                f.write(f"{col:15s}: {change_rate:+.2f} km2/年\n")

        print(f"\n分析完成! 结果已保存至: {output_dir}")

    except Exception as e:
        print(f"分析过程中发生错误: {str(e)}")
        raise


if __name__ == "__main__":
    # 设置路径
    input_directory = r"E:\\GEOdata\\LUCC\\1980-2023_1kmCNLUCC\\CNLUCC_clipped"  # 替换为裁剪后的数据目录
    output_directory = r"E:\\GEOdata\\LUCC\\1980-2023_1kmCNLUCC\\Grassland_Analysis"  # 分析结果输出目录

    # 执行分析
    results = analyze_grassland_change(input_directory, output_directory)
    print("分析完成！结果已保存至:", output_directory)
    #成功运行