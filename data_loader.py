import xarray as xr 
import rioxarray as rio 
import netCDF4
import pandas as pd
import numpy as np
import math
import random
import matplotlib.pyplot as plt

class DataLoader:
    '''The DataLoader class has functions to load and process Sentinel
    L3 data. Three are functions to load the data from a file, and get the color data
    needed to map the data onto the globe.'''

    LAT_RANGE = np.pi
    LON_RANGE = 2 * np.pi

    def __init__(self, sample_count):
        super(DataLoader, self).__init__()
        self.data_file = None
        self.variable_name = None
        self.data = None
        self.lon = None
        self.lon_length = None
        self.lat = None
        self.lat_length = None

        # describes the angle of the approximate circle a single sample point covers
        self.sample_arc = np.arcsin(2 / np.sqrt(sample_count))

    def load_file(self, file_name):
        if file_name == '':
            self.data_file = None
            self.variable_name = None
            self.data = None
            self.lon = None
            self.lon_length = None
            self.lat = None
            self.lat_length = None
            self.name = None
            self.unit = None
            return
        
        self.data_file = netCDF4.Dataset(file_name, mode='r')

        non_data_variables = ['datetime_start', 'datetime_stop', 'count', 'weight', 'latitude', 'longitude']
        for variable in self.data_file.variables:
            if variable not in non_data_variables:
                self.data = self.data_file.variables[variable]
                self.unit = self.data.units
                self.name = self.data.name.replace('_', ' ')
                self.data = self.data[:][0]
                break

        self.lon = self.data_file.variables['longitude'][:]
        self.lon_length = len(self.lon)
        self.lat = self.data_file.variables['latitude'][:]
        self.lat_length = len(self.lat)

        # calculate the amount of indices that any sample point need to include
        # self.lon_index_offset = int(np.floor(self.sample_arc / self.LON_RANGE * self.lon_length))
        # self.lat_index_offset = int(np.floor(self.sample_arc / self.LAT_RANGE * self.lat_length))

        self.lon_index_offset = 2
        self.lat_index_offset = 2

    def convert_data_to_colors(self, points):
        values = np.array([])
        points_to_be_deleted = []
        min_value = None
        max_value = None
        for i in range(len(points)):
            # print(f'point {i}')
            p = points[i]
            x = p[0]
            # lon = 0 is at x = -1. Flip x coord for calcs
            x *= -1
            y = p[1]
            z = p[2]

            # calculate lat and lon for sample point
            lat = np.arcsin(y)
            lon = np.arctan2(z, x)

            # calculate index of sample point in data array
            lat_middle_index = np.round(lat / self.LAT_RANGE * self.lat_length + self.lat_length / 2)
            lon_middle_index = np.round(lon / self.LON_RANGE * self.lon_length + self.lon_length / 2)

            value = 0

            # loop through range of lat and lon indices where values need to be averaged
            # Note: not possible using array indexing because indices outside of range need to be looped back to the other side
            for lat_index in range(self.lat_index_offset * 2 + 1):
                lat_index += lat_middle_index
                lat_index -= self.lat_index_offset

                # if lat_index is now out of range, lon needs to be moved to 180 degrees the opposite side
                if lat_index < 0:
                    lat_out_of_range = True
                    lat_index = -1 * lat_index - 1
                elif lat_index >= self.lat_length:
                    lat_out_of_range = True
                    lat_index = lat_index - (lat_index - self.lat_length)
                else:
                    lat_out_of_range = False

                for lon_index in range(self.lon_index_offset * 2 + 1):
                    lon_index += lon_middle_index
                    lon_index -= self.lon_index_offset

                    # if lat is out of range, we move the sample point to 180 degrees lon to the west
                    # (moving over the top or bottom of lat, means moving to the other side of the planet)
                    if lat_out_of_range:
                        lon_index -= np.round(self.lon_length / 2)
                        # if the lon_index is now below 0, correct
                        if lon_index < 0:
                            lon_index += self.lon_length

                    # if the lon_index is out of range
                    if lon_index < 0:
                        lon_index += self.lon_length
                    if lon_index >= self.lon_length:
                        lon_index -= self.lon_length

                    # print(f'lon {lon_index} lat {lat_index}')
                    value += self.data[int(lat_index)][int(lon_index)]

            # average value
            value = value / ((self.lat_index_offset * 2 + 1) * (self.lon_index_offset * 2 + 1))

            if math.isnan(value):
                points_to_be_deleted.append(i)
                continue

            if min_value == None or value < min_value:
                min_value = value

            if max_value == None or value > max_value:
                max_value = value

            values = np.append(values, value)

        # normalize values
        values = (values - min_value) / (max_value - min_value)
        self.max_value = max_value
        self.min_value = min_value

        colors = np.array([]).reshape(0, 3)
        for val in values:
            r = val
            g = 0
            b = 1 - val
            colors = np.vstack([colors, np.array([r, g, b])])

        points_to_be_deleted.reverse()
        for i in points_to_be_deleted:
            points.pop(i)

        return colors, points

    def convert_data_to_colors_one_point(self, points, normals, radii):
        values = np.array([])
        points_to_be_deleted = []
        min_value = None
        max_value = None
        for i in range(len(points)):
            # print(f'point {i}')
            p = points[i]
            x = p[0]
            # lon = 0 is at x = -1. Flip x coord for calcs
            x *= -1
            y = p[1]
            z = p[2]

            # calculate lat and lon for sample point
            lat = np.arcsin(y)
            lon = np.arctan2(z, x)

            # calculate index of sample point in data array
            lat_middle_index = np.round(lat / self.LAT_RANGE * self.lat_length + self.lat_length / 2)
            lon_middle_index = np.round(lon / self.LON_RANGE * self.lon_length + self.lon_length / 2)

            # print(f'point {i} lat {lat / np.pi * 180} lon {lon / np.pi * 180} lat index {lat_middle_index} lon index {lon_middle_index}')

            if lat_middle_index >= self.lat_length:
                lat_middle_index = self.lat_length - 1
            if lon_middle_index >= self.lon_length:
                lon_middle_index = self.lon_length - 1

            value = self.data[int(lat_middle_index)][int(lon_middle_index)]

            if math.isnan(value):
                points_to_be_deleted.append(i)
                continue

            if min_value == None or value < min_value:
                min_value = value

            if max_value == None or value > max_value:
                max_value = value

            values = np.append(values, value)

        # normalize values
        values = (values - min_value) / (max_value - min_value)
        self.max_value = max_value
        self.min_value = min_value

        colors = np.array([]).reshape(0, 3)
        for val in values:
            # r = val
            # g = 0
            # b = 1 - val
            if val < 0.5:
                r = 0
                g = val * 2
                b = -2 * (x - 0.5)
            else:
                r = 2 * (val - 0.5)
                g = -2*(val - 2) - 2
                b = 0
            
            colors = np.vstack([colors, np.array([r, g, b])])

        points_to_be_deleted.reverse()
        for i in points_to_be_deleted:
            points.pop(i)
            normals.pop(i)
            radii.pop(i)

        return colors, points, normals, radii
