import rasterio
import numpy as np
import matplotlib.pyplot as plt
from glob import glob
import os

# 1. Path configuration
folder = r'E:\GEOdata\pemefrost\QTP_permfrost_change_data_1961_2020\result1'
file_list = sorted(glob(os.path.join(folder, 'fused_*.tif')))  # Sort files by filename

# 2. Subplot layout (3 rows and 4 columns)
nrows, ncols = 3, 4

# 3. Custom colormap (1 for blue, 0 for gray/white)
from matplotlib.colors import ListedColormap

cmap = ListedColormap(['#e5e5e5', '#1565c0'])  # 0=gray, 1=blue, adjustable

# 4. Plotting
fig, axes = plt.subplots(nrows, ncols, figsize=(18, 10), constrained_layout=True)

for i, file in enumerate(file_list):
    row = i // ncols
    col = i % ncols
    ax = axes[row, col]

    # Open raster file
    with rasterio.open(file) as src:
        data = src.read(1)

    # Clean up NoData values and keep only 0 or 1
    data = np.where((data == 1) | (data == 0), data, 0)

    # Display the raster data
    im = ax.imshow(data, cmap=cmap, vmin=0, vmax=1)

    # Extract period (year range) from the filename
    period = os.path.basename(file).replace('fused_', '').replace('_TTOP.tif', '')
    ax.set_title(f"Period: {period}", fontsize=13)
    ax.axis('off')  # Turn off the axis

    # Add a north arrow (north indicator)
    ax.annotate('N', xy=(0.95, 0.95), xycoords='axes fraction', fontsize=15, ha='center', va='center', color='black')

# 5. Add colorbar (legend for 0=Non-Frozen, 1=Frozen)
fig.colorbar(im, ax=axes, orientation='horizontal', fraction=0.03, pad=0.03,
             ticks=[0, 1], label='Frozen Ground Distribution (0=Non-Frozen, 1=Frozen)')

plt.suptitle('Time-Series Frozen Ground Distribution', fontsize=16)
plt.show()
