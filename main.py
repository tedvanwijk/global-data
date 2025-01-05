import open3d as o3d
from open3d import visualization, geometry
from open3d.visualization import gui
import numpy as np
import random
from PySide6 import QtWidgets, QtGui, QtCore
import win32gui
import sys
import matplotlib.pyplot as plt
import os
from posixpath import join
import urllib.request
from data_loader import DataLoader
from mesh_generator import MeshGenerator
from data_importer import DataImporter

class GlobalData:
    SPHERE_SAMPLES = 10000
    SPHERE_RADIUS = 1.005
    STAR_SAMPLES = 1000
    STAR_RADIUS = 10
    SUN_DISTANCE = 11

    DEFAULT_DATA_MAP_OPACITY = 0.4
    DEFAULT_SUN_ROTATION = 180

    def __init__(self):
        super(GlobalData, self).__init__()

        gui.Application.instance.initialize()

        # Initialize GUI window
        self.window = gui.Application.instance.create_window("Wereldverkenner", 1280, 720)

        # initiate external classes
        self.data_loader = DataLoader(self.SPHERE_SAMPLES, self.SPHERE_RADIUS)
        self.mesh_generator = MeshGenerator()
        self.data_importer = DataImporter()

        # set margins for easy access
        em = self.window.theme.font_size
        self.margins = gui.Margins(0.25 * em, 0.25 * em, 0.25 * em, 0.25 * em)

        self.__create_menu()
        self.__create_simulation_window()
        self.__create_scale()

        # Add items to window
        self.window.set_on_layout(self.__on_layout)
        self.window.add_child(self._scene)
        self.window.add_child(self._menu)
        self.window.add_child(self._scale)
        self.window.add_child(self._scale_upper_label)
        self.window.add_child(self._scale_param_label)
        self.window.add_child(self._scale_lower_label)

        self.__plot_stars()
        self.__create_data_points()

    def __create_simulation_window(self):
        # Set up globe and camera location
        globeLocation = [0, 0, 0]
        cameraLocation = [-4, 0, 0]

        # Create mesh
        globeMesh = geometry.TriangleMesh.create_sphere(create_uv_map=True)
        globeMesh.compute_vertex_normals()
        globeMesh.translate(globeLocation)
        rotMatrix = geometry.get_rotation_matrix_from_xyz([np.pi/2, 0, 0])
        globeMesh.rotate(rotMatrix)

        # Add texture
        globeMat = visualization.rendering.MaterialRecord()
        globeMat.base_color = [0.5, 0.5, 0.5, 1.0]
        globeMat.shader = "defaultLit"
        globeMat.albedo_img = o3d.io.read_image('images/blueMarble_rotated.jpg')
        # globeMat.normal_img = o3d.io.read_image('blueMarbleTop_cropped_rotated.png')
        globeMat.base_reflectance = 0.25
        # globeMat.base_metallic = 0
                            
        # Create 3D scene
        self._scene = gui.SceneWidget()
        self._scene.scene = visualization.rendering.Open3DScene(self.window.renderer)
        self._scene.scene.set_background([0, 0, 0, 1])
        lightningProfile = visualization.rendering.Open3DScene.LightingProfile.SOFT_SHADOWS

        sun_x = np.sin(self.DEFAULT_SUN_ROTATION / 180 * np.pi) * self.SUN_DISTANCE
        sun_y = np.cos(self.DEFAULT_SUN_ROTATION / 180 * np.pi) * self.SUN_DISTANCE

        self._scene.scene.scene.set_sun_light(
            [sun_x, 0, sun_y],  # direction
            [1, 1, 1],  # color
            1000000)  # intensity
        self._scene.scene.scene.enable_sun_light(True)

        # Add mesh to scene
        self._scene.scene.add_geometry('Globe', globeMesh, globeMat)

        # Set up camera for scene
        globeBoundingBox = globeMesh.get_axis_aligned_bounding_box()
        self._scene.setup_camera(40, globeBoundingBox, globeLocation)
        self._scene.look_at(globeLocation, cameraLocation, [0, 1, 0])

    def __create_menu(self):
        em = self.window.theme.font_size
        self._menu = gui.Vert(0, self.margins)
        
        self._menu.add_child(gui.Label("Instellingen"))

        # collection dropdown
        collection_layout = gui.Vert(0, self.margins)

        self.collections = self.data_importer.get_collections()
        self.collection_dropdown = gui.Combobox()

        self.collection_dropdown.add_item('Kies een parameter')
        for collection in self.collections:
            self.collection_dropdown.add_item(collection['title'])

        self.collection_dropdown.set_on_selection_changed(self.__on_collection_dropdown)

        collection_layout.add_child(gui.Label('Parameter'))
        collection_layout.add_child(self.collection_dropdown)

        self._menu.add_child(collection_layout)

        # data range dropdown
        range_layout = gui.Vert(0, self.margins)

        self.range_dropdown = gui.Combobox()
        self.range_dropdown.set_on_selection_changed(self.__on_range_dropdown)

        range_layout.add_child(gui.Label('Parameter range'))
        range_layout.add_child(self.range_dropdown)

        self._menu.add_child(range_layout)

        # data specific range dropdown
        specific_range_layout = gui.Vert(0, self.margins)

        self.specific_range_dropdown = gui.Combobox()
        self.specific_range_dropdown.set_on_selection_changed(self.__on_specific_range_dropdown)

        specific_range_layout.add_child(gui.Label('Parameter range'))
        specific_range_layout.add_child(self.specific_range_dropdown)

        self._menu.add_child(specific_range_layout)

        # dataset dropdown
        dataset_layout = gui.Vert(0, self.margins)

        self.dataset_dropdown = gui.Combobox()
        self.dataset_dropdown.set_on_selection_changed(self.__on_dataset_dropdown)

        dataset_layout.add_child(gui.Label('Let op: het downloaden van data kan even duren'))
        dataset_layout.add_child(gui.Label('Dataset'))
        dataset_layout.add_child(self.dataset_dropdown)
        dataset_layout.add_child(gui.Label('Data wordt opgeslagen in downloaded_data. Dit kan veel ruimte opnemen. Leeg de map indien nodig.'))

        self._menu.add_child(dataset_layout)

        # sun slider
        sun_slider_layout = gui.Horiz(0, self.margins)

        sun_slider = gui.Slider(gui.Slider.INT)
        sun_slider.set_limits(0, 360)
        sun_slider.set_on_value_changed(self.__on_sun_slider)
        sun_slider.int_value = self.DEFAULT_SUN_ROTATION

        sun_slider_layout.add_child(gui.Label('Zon locatie'))
        sun_slider_layout.add_child(sun_slider)

        self._menu.add_child(sun_slider_layout)

        # opacity slider
        opacity_slider_layout = gui.Horiz(0, self.margins)

        opacity_slider = gui.Slider(gui.Slider.DOUBLE)
        opacity_slider.set_limits(0, 1)
        opacity_slider.set_on_value_changed(self.__on_opacity_slider)
        opacity_slider.double_value = self.DEFAULT_DATA_MAP_OPACITY

        opacity_slider_layout.add_child(gui.Label('Doorzichtigheid'))
        opacity_slider_layout.add_child(opacity_slider)

        self._menu.add_child(opacity_slider_layout)
        
    def __create_scale(self):
        self._scale = gui.ImageWidget('./images/scale.jpg')
        self._scale.ui_image.scaling = gui.UIImage.Scaling.ANY

        self._scale_param_label = gui.Label('')
        self._scale_upper_label = gui.Label('')
        self._scale_lower_label = gui.Label('')

        self._scale_param_label.background_color = gui.Color(1, 1, 1, 0)
        self._scale_lower_label.background_color = gui.Color(1, 1, 1, 0)
        self._scale_upper_label.background_color = gui.Color(1, 1, 1, 0)

    def __on_opacity_slider(self, opacity):
        self.data_map_mat.base_color = [1, 1, 1, opacity]
        self._scene.scene.modify_geometry_material('data_map', self.data_map_mat)

    def __on_sun_slider(self, rotation):
        sun_x = np.sin(rotation / 180 * np.pi) * self.SUN_DISTANCE
        sun_y = np.cos(rotation / 180 * np.pi) * self.SUN_DISTANCE

        self._scene.scene.scene.set_sun_light(
            [sun_x, 0, sun_y],  # direction
            [1, 1, 1],  # color
            1000000)  # intensity

    def __on_collection_dropdown(self, collection_title, index):
        self.collection_dropdown.selected_text = collection_title
        self.__delete_data_map()
        self.range_dropdown.clear_items()
        self.specific_range_dropdown.clear_items()
        self.dataset_dropdown.clear_items()

        if index == 0:
            return
        
        for collection in self.collections:
            if collection_title == collection['title']:
                self.selected_collection = collection
                break
        
        self.data_importer.get_links(self.selected_collection['href'])

        ranges = ['Kies een range', 'dag', '3 dagen', 'maand', 'seizoen', 'jaar']
        for range in ranges:
            self.range_dropdown.add_item(range)
        
    def __on_range_dropdown(self, range, index):
        self.range_dropdown.selected_text = range
        self.__delete_data_map()
        self.specific_range_dropdown.clear_items()
        self.dataset_dropdown.clear_items()

        if index == 0:
            return
        
        ranges = ['', 'day', '3day', 'month', 'season', 'year']
        self.selected_range = ranges[index]

        href = join(self.selected_collection['href'], ranges[index])
        links = self.data_importer.get_links(href)

        self.specific_range_dropdown.add_item('Kies specifieke range')

        for link in links:
            if link['rel'] == 'child':
                self.specific_range_dropdown.add_item(link['title'])

    def __on_specific_range_dropdown(self, specific_range, index):
        self.specific_range_dropdown.selected_text = specific_range
        self.__delete_data_map()
        self.dataset_dropdown.clear_items()

        if index == 0:
            return
        
        href = join(self.selected_collection['href'], specific_range)
        links = self.data_importer.get_links(href)

        self.dataset_dropdown.add_item('Kies item')

        for link in links:
            if link['rel'] == 'item':
                self.dataset_dropdown.add_item(link['title'])

    def __on_dataset_dropdown(self, dataset, index):
        self.dataset_dropdown.selected_text = dataset
        self.__delete_data_map()

        if index == 0:
            return
        
        href = join(self.selected_collection['href'], self.specific_range_dropdown.selected_text, f'{dataset}.json')
        json = self.data_importer.get_json(href)

        download_link = json['assets']['product']['href']

        if not os.path.isfile(f'./downloaded_data/{dataset}.nc'):
            urllib.request.urlretrieve(download_link, f'./downloaded_data/{dataset}.nc')
        self.__create_data_map(f'./downloaded_data/{dataset}.nc')

    def __on_layout(self, layout_context):
        r = self.window.content_rect
        self._scene.frame = r

        menu_width = 300
        menu_height = r.height
        self._menu.frame = gui.Rect(r.get_right() - menu_width, r.y, menu_width, menu_height)

        scale_width = 50
        scale_height = r.height
        self._scale.frame = gui.Rect(0, r.y, scale_width, scale_height)

        scale_label_height = 20
        scale_label_width = r.width
        padding = self.window.theme.font_size * 0.25
        self._scale_param_label.frame = gui.Rect(scale_width + padding, r.y, scale_label_width, scale_label_height)
        self._scale_upper_label.frame = gui.Rect(scale_width + padding, r.y + scale_label_height, scale_label_width, scale_label_height)
        self._scale_lower_label.frame = gui.Rect(scale_width + padding, r.height - scale_label_height, scale_label_width, scale_label_height)

    def __create_data_points(self):
        mat = visualization.rendering.MaterialRecord()
        mat.has_alpha = True
        mat.base_color = [1, 1, 1, self.DEFAULT_DATA_MAP_OPACITY]
        mat.shader = "defaultUnlitTransparency"
        self.data_map_mat = mat

        points, colors, normals, radii = self.mesh_generator.generate_sphere_points(self.SPHERE_RADIUS, self.SPHERE_SAMPLES)
        self.data_points_list = points

        points = o3d.utility.Vector3dVector(points)
        colors = o3d.utility.Vector3dVector(colors)
        normals = o3d.utility.Vector3dVector(normals)
        radii = o3d.utility.DoubleVector(radii)

        pcd = o3d.geometry.PointCloud(points) 
        pcd.colors = colors
        pcd.normals = normals

        self.data_points = pcd

    def __delete_data_map(self):
        self._scene.scene.remove_geometry('data_map')

    def __create_data_map(self, file_path):
        self.data_loader.load_file(file_path)
        colors, points = self.data_loader.convert_data_to_colors_one_point(self.data_points_list)
        self._scale_param_label.text = self.data_loader.name
        self._scale_lower_label.text = f'{self.data_loader.min_value} {self.data_loader.unit}'
        self._scale_upper_label.text = f'{self.data_loader.max_value} {self.data_loader.unit}'
        
        self.data_points.colors = o3d.utility.Vector3dVector(colors)
        self.data_points.points = o3d.utility.Vector3dVector(points)

        # mesh = geometry.TriangleMesh.create_from_point_cloud_ball_pivoting(pcd, radii)
        mesh = geometry.TriangleMesh.create_from_point_cloud_alpha_shape(self.data_points, 1000)
        # mesh = geometry.TriangleMesh.create_from_point_cloud_poisson(self.data_points)[0]

        self._scene.scene.add_geometry('data_map', mesh, self.data_map_mat)
        # self._scene.scene.add_geometry('data_map', self.data_points, self.data_map_mat)

    def __plot_stars(self):
        mat = visualization.rendering.MaterialRecord()
        mat.base_color = [1.0, 1.0, 1.0, 1.0]
        mat.shader = "defaultUnlit"

        points, colors = self.mesh_generator.generate_random_sphere_points(self.STAR_RADIUS, self.STAR_SAMPLES)
        pcd = o3d.t.geometry.PointCloud(points)
        pcd.point.colors = colors
        self._scene.scene.add_geometry('stars', pcd, mat)

    def run(self):
        gui.Application.instance.run()

if __name__ == '__main__':
    globalData = GlobalData()
    globalData.run()