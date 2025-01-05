import numpy as np
import math
import random

class MeshGenerator:
    def __init__(self):
        super(MeshGenerator, self).__init__()

    def generate_sphere_points(self, sphere_radius, point_count):
        points = []
        colors = []
        normals = []
        radii = []
        phi = np.pi * (np.sqrt(5.) - 1.)  # golden angle in radians

        for i in range(point_count):
            y = sphere_radius - (i / float(point_count - 1)) * (2 * sphere_radius)  # y goes from 1 to -1
            radius = np.sqrt(sphere_radius - y * y)  # radius at y

            theta = phi * i  # golden angle increment

            x = np.cos(theta) * radius
            z = np.sin(theta) * radius

            if math.isnan(x) or math.isnan(y) or math.isnan(z):
                continue

            x_norm = x / np.sqrt(x * x + y * y + z * z)
            y_norm = y / np.sqrt(x * x + y * y + z * z)
            z_norm = z / np.sqrt(x * x + y * y + z * z)

            points.append((x, y, z))
            colors.append((min(x_norm, 0), min(y_norm, 0), min(z_norm, 0)))
            normals.append((x_norm, y_norm, z_norm))
            radii.append(1)

        return points, colors, normals, radii
    
    def generate_random_sphere_points(self, sphere_radius, point_count):
        points = []
        colors = []
        i = 0
        while i < point_count:
            x = random.gauss()
            y = random.gauss()
            z = random.gauss()

            if x == 0 and y == 0 and z == 0:
                continue
            else:
                i += 1
            
            x_norm = x / np.sqrt(x * x + y * y + z * z) * sphere_radius
            y_norm = y / np.sqrt(x * x + y * y + z * z) * sphere_radius
            z_norm = z / np.sqrt(x * x + y * y + z * z) * sphere_radius

            color = random.uniform(0, 1)

            points.append((x_norm, y_norm, z_norm))
            colors.append((color, color, color))
        return points, colors