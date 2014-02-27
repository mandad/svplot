import os
if os.name != 'posix':
    here = os.getcwd()
    # hstp = r'C:\Program Files (x86)\Pydro\Lib\site-packages\HSTP\Pydro'
    hstp = r'C:\Program Files\Pydro64\Lib\site-packages\HSTP\Pydro'
    os.chdir(hstp)
import gdal
from gdalconst import *
import osr
import sys
if os.name != 'posix':
    os.chdir(here)

def ConvertToGTiff(filename, x_lim, y_lim, utm_zone):
    """Creates a GeoTiff with the same file name as that passed to it"""
    # Create new GTiff file as a copy of the png
    src_ds = gdal.Open(filename)
    # ds_info = src_ds.GetMetadata_Dict()
    # print src_ds.RasterXSize, src_ds.RasterYSize, src_ds.RasterCount
    format = "GTiff"
    driver = gdal.GetDriverByName(format)
    options = ['COMPRESS=LZW', 'PREDICTOR=2']
    dst_ds = driver.CreateCopy(filename[:-3] + 'tif' , src_ds, 0, options=options)

    # Set GeoReference info
    pixel_size_x = (x_lim[1] - x_lim[0]) / src_ds.RasterXSize
    pixel_size_y = (y_lim[1] - y_lim[0]) / src_ds.RasterYSize

    # padfTransform is the array passed to SetGeoTransform
    # Xp = padfTransform[0] + P*padfTransform[1] + L*padfTransform[2];
    # Yp = padfTransform[3] + P*padfTransform[4] + L*padfTransform[5];
    # [top left px x, E-W width dx, N-S height dx, top left pixel y, E-W width dy, N-S height dy] 
    dst_ds.SetGeoTransform([x_lim[0], pixel_size_x, 0, y_lim[1], 0, -pixel_size_y]) 
    srs = osr.SpatialReference()
    srs.SetUTM(utm_zone, 1)  # zone, north = 1
    srs.SetWellKnownGeogCS('NAD83')
    dst_ds.SetProjection(srs.ExportToWkt())

    # Properly close the datasets
    dst_ds = None
    src_ds = None

def main():
    if len(sys.argv) == 7:
        pass

if __name__ == '__main__':
    main()