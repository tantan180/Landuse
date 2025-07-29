import matplotlib.pyplot as plt
import numpy as np

# 假设这些是你已有的年份数据和冻土面积数据
years = np.array([1965, 1970, 1975, 1980, 1985, 1990, 1995,2000, 2005,2010, 2015, 2020])
frozen_area = np.array([148561.0, 148464.0, 148350.0, 148162.0, 147271.0, 145913.0, 145869.0, 146988.0, 140593.0, 136257.0, 141153.0, 128447.0])

# 绘制原始数据
plt.plot(years, frozen_area, marker='o', label='Frozen Area')

# 计算趋势线
slope, intercept = np.polyfit(years, frozen_area, 1)  # 线性回归，拟合一次多项式
trendline = slope * years + intercept  # 计算趋势线

# 绘制趋势线
plt.plot(years, trendline, color='red', linestyle='--', label='Average Trend Line')

# 添加标题和标签
plt.title('Frozen Ground Area Change Trend in Research Area')
plt.xlabel('Year')
plt.ylabel('Frozen Area (km²)')

# 显示图例
plt.legend()

# 显示图形
plt.show()
