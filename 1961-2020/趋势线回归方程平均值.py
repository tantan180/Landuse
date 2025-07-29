import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D

# Input data: Periods and corresponding frozen area values
years = np.array([1961, 1966, 1971, 1976, 1981, 1986, 1991, 1996, 2001, 2006, 2011, 2016])
frozen_area = np.array([148561, 148464, 146350, 148162, 147271, 145913, 145869, 146988, 140593, 136257, 141153, 128447])

# Calculate average values for each decade
decade_avg = {
    '1966-1970': np.mean(frozen_area[:2]),
    '1971-1980': np.mean(frozen_area[2:4]),
    '1981-1990': np.mean(frozen_area[4:6]),
    '1991-2000': np.mean(frozen_area[6:8]),
    '2001-2010': np.mean(frozen_area[8:10]),
    '2011-2020': np.mean(frozen_area[10:])
}

# Plot the graph
plt.figure(figsize=(10, 6))
plt.plot(years, frozen_area, marker='o', label="Frozen Area", color='blue')

# Add the trendline (linear fit)
p = np.polyfit(years, frozen_area, 1)
trendline = np.polyval(p, years)
plt.plot(years, trendline, color='red', linestyle='-', label=f'Trendline: y = {p[0]:.2f}x + {p[1]:.2f}')

# Add the average lines for each decade
for i, (period, avg) in enumerate(decade_avg.items()):
    start_year, end_year = map(int, period.split('-'))
    avg_line = np.array([avg] * (end_year - start_year + 1))
    avg_years = np.arange(start_year, end_year + 1)
    plt.plot(avg_years, avg_line, linestyle='--', label=f'{period} Avg')

    # Add arrows for the average value and annotate
    plt.annotate(f'{avg:.0f}', xy=(end_year, avg), xytext=(end_year + 0.5, avg),
                 arrowprops=dict(facecolor='black', arrowstyle='->'), fontsize=10)

# Add labels and title
plt.title('Frozen Ground Area Change with Trendline and 10-Year Averages')
plt.xlabel('Year')
plt.ylabel('Frozen Area (km²)')

# Add legend
plt.legend(loc='lower left')

# Show the plot
plt.tight_layout()
plt.show()
