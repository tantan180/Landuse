import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# 设置中文字体
plt.rcParams["font.family"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False  # 正确显示负号

# 1. 准备数据（基于之前的分段结果）
data = {
    "阶段": [
        "1961-1970", "1971-1980", "1981-1990",
        "1991-2000", "2001-2010", "2011-2020"
    ],
    "年平均退化速率（km²/年）": [
        -19.4, -30.2, -224.9,
        107.5, -1073.1, -781.0
    ],
    "加速点标注年份": [None, None, None, None, 2000, 2015]  # 加速点对应的年份
}

df = pd.DataFrame(data)

# 2. 创建图表
plt.figure(figsize=(12, 6))

# 绘制柱状图
bars = plt.bar(
    df["阶段"],
    df["年平均退化速率（km²/年）"],
    color=np.where(df["年平均退化速率（km²/年）"] < 0, "salmon", "lightgreen"),
    edgecolor="black"
)

# 3. 标注加速点
for i, (rate, year) in enumerate(zip(df["年平均退化速率（km²/年）"], df["加速点标注年份"])):
    if year is not None:
        # 箭头指向对应柱子，标注年份和速率
        plt.annotate(
            f"加速点（{year}年）\n速率: {rate:.1f} km²/年",
            xy=(i, rate),
            xytext=(i+0.5, rate-500 if rate < 0 else rate+500),
            arrowprops=dict(facecolor="red", shrink=0.05, width=2),
            fontsize=10,
            color="red",
            bbox=dict(facecolor="white", edgecolor="red", pad=3)
        )

# 4. 添加参考线和标签
plt.axhline(y=0, color="gray", linestyle="--")  # 零值参考线（区分增加/减少）
plt.xlabel("时间段", fontsize=12)
plt.ylabel("年平均退化速率（km²/年）", fontsize=12)
plt.title("1961-2020年冻土退化速率分段对比（含加速点）", fontsize=14)
plt.grid(axis="y", linestyle="--", alpha=0.7)

# 5. 在柱子上方标注具体数值
for bar in bars:
    height = bar.get_height()
    plt.text(
        bar.get_x() + bar.get_width()/2.,
        height + 50 if height > 0 else height - 100,
        f"{height:.1f}",
        ha="center",
        fontsize=9
    )

# 6. 保存图表
plt.tight_layout()
output_path = r"E:\GEOdata\pemefrost\QTP_permfrost_change_data_1961_2020\picture\冻土退化速率分段对比.png"
plt.savefig(output_path, dpi=300, bbox_inches="tight")
print(f"图表已保存至: {output_path}")

plt.show()