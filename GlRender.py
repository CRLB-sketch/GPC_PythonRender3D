########################################################################################
"""
    Universidad del Valle de Guatemala
    Graficas por Computadora
    Python Render3D
"""
__author__ = "Cristian Laynez 201281"
__status__ = "Student of Computer Science"

# ! GL Render : Clase donde esta todo el Gl personalizado
# Referencias de Carlos Alonso proporcionado en clase
######################################################################################

import struct
from collections import namedtuple

from math import cos, sin, tan, pi
from turtle import width

from Obj import Obj
from Texture import Texture

from MathFake import MathFake as mf

V2 = namedtuple('Point2', ['x', 'y'])
V3 = namedtuple('Point3', ['x', 'y', 'z'])
V4 = namedtuple('Point4', ['x', 'y', 'z', 'w'])

def color(r : int, g : int, b : int): return bytes([int(b * 255), int(g * 255), int(r * 255)])

def bary_coords(A, B, C, P) -> list:
    areaPBC = (B.y - C.y) * (P.x - C.x) + (C.x - B.x) * (P.y - C.y)
    areaPAC = (C.y - A.y) * (P.x - C.x) + (A.x - C.x) * (P.y - C.y)
    areaABC = (B.y - C.y) * (A.x - C.x) + (C.x - B.x) * (A.y - C.y)

    try:
        # PBC / ABC
        u = areaPBC / areaABC
        # PAC / ABC
        v = areaPAC / areaABC
        # 1 - u - v
        w = 1 - u - v
    except:
        return -1, -1, -1
    
    return u, v, w

class Renderer(object):
    def __init__(self, width : int, height : int):
        self.__gl_init(width, height)
    
    def __gl_init(self, width : int, height : int) -> None:
        self.__gl_create_window(width, height) 
        self.clear_color = color(0, 0, 0)
        self.current_color = color(1, 1, 1)   
        
        # Definir más atributos
        self.active_shader = None
        # Para activar más texturas
        self.active_texture1 = None
        self.active_texture2 = None
        # Normal map
        self.normal_map = None
        
        self.dir_light = V3(0, 0, -1)
        
        self.gl_view_matrix()        
        self.gl_clear()             

    def __gl_create_window(self, width : int, height : int) -> None:
        self.width = width
        self.height = height
        self.gl_view_port(0, 0, self.width, self.height)

    def gl_view_port(self, pos_x : int, pos_y : int, width : int, height : int) -> None:
        self.vp_x = pos_x
        self.vp_y = pos_y
        self.vp_width = width
        self.vp_height = height
        
        self.view_port_matrix = [
            [width/2, 0, 0, pos_x + width/2],
            [0, height/2, 0, pos_y + height/2],
            [0, 0, 0.5, 0.5],
            [0, 0, 0, 1]
        ]
        
        self.gl_projection_matrix()

    def gl_view_matrix(self, translate = V3(0, 0, 0), rotate = V3(0, 0, 0)) -> None:
        self.cam_matrix = self.__gl_create_object_matrix(translate, rotate)
        self.view_matrix = mf.linalg_inversion(self.cam_matrix)
        
    def gl_look_at(self, eye : V3, cam_position = V3(0, 0, 0)) -> None:
        forward = mf.subtract_V3(cam_position, eye)
        forward = mf.divition([forward[0], forward[1], forward[2]], mf.norm(forward))
        
        right = mf.cross([0, 1, 0], forward)
        right = mf.divition(right, mf.norm(right))
        
        up = mf.cross(forward, right)
        up = mf.divition(up, mf.norm(up))
        
        self.cam_matrix = [
            [right[0], up[0], forward[0], cam_position[0]],
            [right[1], up[1], forward[1], cam_position[1]],
            [right[2], up[2], forward[2], cam_position[2]],
            [0, 0, 0, 1]
        ]
        
        self.view_matrix = mf.linalg_inversion(self.cam_matrix)

    def gl_projection_matrix(self, n = 0.1, f = 1000, fov = 60) -> None:
        aspect_ratio = self.vp_width / self.vp_height
        t = tan( (fov * pi / 180) / 2) * n
        r = t * aspect_ratio
        
        self.projection_matrix = [
            [n/r,0,0,0],
            [0,n/t,0,0],
            [0,0,-(f+n)/(f-n),-(2*f*n)/(f-n)],
            [0,0,-1,0]
        ]

    def gl_clear_color(self, r : int, g : int, b : int) -> None: self.clear_color = color(r, g, b)

    def gl_color(self, r : int, g : int, b : int) -> None: self.current_color = color(r,g,b)

    def gl_clear(self) -> None:
        self.pixels = [[ self.clear_color for y in range(self.height)] for x in range(self.width)]
        self.zbuffer = [[ float('inf') for y in range(self.height)] for x in range(self.width)]

    def gl_clear_viewport(self, clr = None) -> None:
        for x in range(self.vp_x, self.vp_x + self.vp_width):
            for y in range(self.vp_y, self.vp_y + self.vp_height):
                self.gl_point(x, y, clr)

    def gl_point(self, x : int, y : int, clr = None) -> None:
        if ( 0 <= x < self.width) and (0 <= y < self.height):
            self.pixels[x][y] = clr or self.current_color

    def gl_point_vp(self, ndcX : int, ndcY : int, clr = None) -> None:
        if ndcX < -1 or ndcX > 1 or ndcY < -1 or ndcY > 1:
            return
        x = int((ndcX + 1) * (self.vp_width / 2) + self.vp_x)
        y = int((ndcY + 1) * (self.vp_height / 2) + self.vp_y)        
        self.gl_point(x, y, clr)

    def gl_create_rotation_matrix(self, pitch = 0, yaw = 0, roll = 0):        
        pitch *= pi / 180
        yaw *= pi / 180
        roll *= pi / 180
        
        pitch_mat = [
            [1, 0, 0, 0],
            [0, cos(pitch),-sin(pitch), 0],
            [0, sin(pitch), cos(pitch), 0],
            [0, 0, 0, 1]
        ]
        
        yaw_mat = [
            [cos(yaw), 0, sin(yaw), 0],
            [0, 1, 0, 0],
            [-sin(yaw), 0, cos(yaw), 0],
            [0, 0, 0, 1]
        ]
        
        roll_mat = [
            [cos(roll),-sin(roll), 0, 0],
            [sin(roll), cos(roll), 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 1]
        ]
        
        return mf.multiply_matrixs([pitch_mat, yaw_mat, roll_mat])

    def gl_line(self, v0 : V2, v1 : V2, clr = None) -> None:
        # Implementación del algoritmo de la linea de Bresenham [ y = m * x + b ] 
        x0 = int(v0.x)
        x1 = int(v1.x)
        y0 = int(v0.y)
        y1 = int(v1.y)
        
        # Se dibujará un solo punto si dado caso el punto#0 es igual al punto#1
        if x0 == x1 and y0 == y1:
            self.gl_point(x0, y0, clr)
            return
        
        dy = abs(y1 - y0)
        dx = abs(x1 - x0)

        steep = dy > dx

        # Se realizará un intercambio de puntos si la pendiente es mayor a 1 o menor a -1  
        if steep:
            x0, y0 = y0, x0
            x1, y1 = y1, x1
            
        # Se realizará un intercambio de puntos si el punto inicial X es más grande que el punto final X
        if x0 > x1:
            x0, x1 = x1, x0
            y0, y1 = y1, y0

        dy = abs(y1 - y0)
        dx = abs(x1 - x0)

        offset = 0
        limit = 0.5
        m = dy / dx
        y = y0

        for x in range(x0, x1 + 1):
            # Dibujar de manera vertical si dado caso la pendendiente es mayor a 1 o meor a -1
            # Si dado caso no se dibujará de manera horizontal
            self.gl_point(y, x, clr) if steep else self.gl_point(x, y, clr)

            offset += m

            if offset >= limit:
                y = y + 1 if y0 < y1 else y - 1                
                limit += 1                
                
    def draw_polygon(self, polygon : list, clr = None) -> None:
        for i in range(len(polygon)):
            self.gl_line(polygon[i], polygon[ (i + 1) % len(polygon)], clr)
            
        self.__filling_polygon(polygon, clr, clr)

    def __filling_polygon(self, polygon : list, clr_check : color, clr_fill : color) -> None:
        x_min = polygon[0].x
        y_min = polygon[0].y
        x_max = polygon[0].x
        y_max = polygon[0].y

        # De primero vamos a obtener los puntos minimos y maximos de los puntos
        for i in range(len(polygon)):
            if polygon[i].x < x_min:
                x_min = polygon[i].x
            if polygon[i].y < y_min:
                y_min = polygon[i].y
            if polygon[i].x > x_max:
                x_max = polygon[i].x
            if polygon[i].y > y_max:
                y_max = polygon[i].y

        central_x = int((x_max + x_min) / 2)
        central_y = int((y_max + y_min) / 2)
        
        def filling_boundary_1(x : int, y : int, clr_check : color, clr_fill : color) -> None:
            if(self.pixels[x][y] != clr_check):
                self.gl_point(x, y, clr_fill)                
                filling_boundary_1(x , y + 1, clr_fill, clr_check)
                filling_boundary_1(x - 1, y, clr_fill, clr_check)                
                filling_boundary_1(x + 1, y, clr_fill, clr_check)
        
        def filling_boundary_2(x : int, y : int, clr_check : color, clr_fill : color) -> None:
            if(self.pixels[x][y] != clr_check):
                self.gl_point(x, y, clr_fill)
                filling_boundary_2(x, y - 1, clr_fill, clr_check)
                filling_boundary_2(x - 1, y, clr_fill, clr_check) 
                filling_boundary_2(x + 1, y, clr_fill, clr_check)
                            
        filling_boundary_1(central_x, central_y, clr_check, clr_fill)
        self.gl_point(central_x, central_y, color(0, 0, 0))
        filling_boundary_2(central_x, central_y, clr_check, clr_fill)
        # PD: Tuve que separar la recursividad en 2 para evitar problemas de "Maximum recursion depth exceeded"

    def gl_load_model(self, filename : str, translate = V3(0, 0, 0), rotate = V3(0, 0, 0), scale = V3(1, 1, 1)) -> None:
        model = Obj(filename)
        model_matrix = self.__gl_create_object_matrix(translate, rotate, scale)
        rotation_matrix = self.gl_create_rotation_matrix(rotate[0], rotate[1], rotate[2])
        
        for face in model.faces:
            vert_count = len(face)            
            
            v0 = model.vertices[ face[0][0] - 1]
            v1 = model.vertices[ face[1][0] - 1]
            v2 = model.vertices[ face[2][0] - 1]
            
            v0 = self.__gl_transform(v0, model_matrix)
            v1 = self.__gl_transform(v1, model_matrix)
            v2 = self.__gl_transform(v2, model_matrix)
                        
            A = self.gl_cam_transform(v0)
            B = self.gl_cam_transform(v1)
            C = self.gl_cam_transform(v2)
                        
            vt0 = model.texcoords[face[0][1] - 1]
            vt1 = model.texcoords[face[1][1] - 1]
            vt2 = model.texcoords[face[2][1] - 1]

            vn0 = model.normals[face[0][2] - 1]
            vn1 = model.normals[face[1][2] - 1]
            vn2 = model.normals[face[2][2] - 1]
            
            vn0 = self.gl_dir_transform(vn0, rotation_matrix)
            vn1 = self.gl_dir_transform(vn1, rotation_matrix)
            vn2 = self.gl_dir_transform(vn2, rotation_matrix)
            
            self.__gl_triangle_bc(A, B, C, 
                                  verts = (v0, v1, v2), 
                                  tex_coords= (vt0, vt1, vt2), 
                                  normals = (vn0, vn1, vn2))
            
            if vert_count == 4:
                v3 = model.vertices[ face[3][0] - 1]
                v3 = self.__gl_transform(v3, model_matrix)
                D = self.gl_cam_transform(v3)
                vt3 = model.texcoords[face[3][1] - 1]
                vn3 = model.normals[face[3][2] - 1]
                vn3 = self.gl_dir_transform(vn3, rotation_matrix)
                
                self.__gl_triangle_bc(A, C, D, 
                                      verts = (v0, v2, v3), 
                                      tex_coords= (vt0, vt2, vt3), 
                                      normals = (vn0, vn2, vn3))       
                                                        
    def __gl_create_object_matrix(self, translate = V3(0, 0, 0), rotate = V3(0, 0, 0), scale = V3(1, 1, 1)):        
        translation = [
            [1, 0, 0, translate.x],
            [0, 1, 0, translate.y],
            [0, 0, 1, translate.z],
            [0, 0, 0, 1]
        ]

        # rotation = mf.identity(4)
        rotation = self.gl_create_rotation_matrix(rotate.x, rotate.y, rotate.z) # ! OJO

        scale_mat = [
            [scale.x, 0, 0, 0],
            [0, scale.y, 0, 0],
            [0, 0, scale.z, 0],
            [0, 0, 0, 1]
        ]
        
        return mf.multiply_matrixs([translation, rotation, scale_mat])
        
    def __gl_transform(self, vertex, matrix) -> V3:
        v = V4(vertex[0], vertex[1], vertex[2], 1)
        vt = mf.multiply_matrix_and_v4(matrix, v) # Multiplicando una matriz y un vector
        vf = V3(vt[0] / vt[3],
                vt[1] / vt[3],
                vt[2] / vt[3])
        return vf
    
    def gl_dir_transform(self, dir_vector, rot_matrix):
        v = V4(dir_vector[0], dir_vector[1], dir_vector[2], 0)
        vt = mf.multiply_matrix_and_v4(rot_matrix, v)
        vf = V3(vt[0], vt[1], vt[2])
        return vf # TODO listo supongo yo
    
    def gl_cam_transform(self, vertex):
        v = V4(vertex[0], vertex[1], vertex[2], 1)
        vt = mf.multiply_matrix_and_v4(
            mf.multiply_matrixs(
                [self.view_port_matrix, self.projection_matrix, self.view_matrix]
            ), v)
        vf = V3(vt[0] / vt[3],
                vt[1] / vt[3],
                vt[2] / vt[3])
        return vf # TODO listo supongo yo
    
    def __gl_triangle_std(self, A : V3, B : V3, C : V3, clr = None) -> None:        
        if A.y < B.y:
            A, B = B, A
        if A.y < C.y:
            A, C = C, A
        if B.y < C.y:
            B, C = C, B

        self.gl_line(A,B, clr)
        self.gl_line(B,C, clr)
        self.gl_line(C,A, clr)
        
        def flat_bottom(vA : V3, vB : V3, vC : V3) -> None:
            try:
                mBA = (vB.x - vA.x) / (vB.y - vA.y)
                mCA = (vC.x - vA.x) / (vC.y - vA.y)
            except:
                pass
            else:
                x0 = vB.x
                x1 = vC.x
                for y in range(int(vB.y), int(vA.y)):
                    self.gl_line(V2(x0, y), V2(x1, y), clr)
                    x0 += mBA
                    x1 += mCA

        def flat_top(vA : V3, vB : V3, vC : V3) -> None:
            try:
                mCA = (vC.x - vA.x) / (vC.y - vA.y)
                mCB = (vC.x - vB.x) / (vC.y - vB.y)
            except:
                pass
            else:
                x0 = vA.x
                x1 = vB.x
                for y in range(int(vA.y), int(vC.y), -1):
                    self.gl_line(V2(x0, y), V2(x1, y), clr)
                    x0 -= mCA
                    x1 -= mCB

        if B.y == C.y:
            # Parte plana abajo
            flat_bottom(A,B,C)
        elif A.y == B.y:
            # Parte plana arriba
            flat_top(A,B,C)
        
        # Dibujo ambos tipos de triangulos
        # Teorema de intercepto
        D = V2( A.x + ((B.y - A.y) / (C.y - A.y)) * (C.x - A.x), B.y)
        flat_bottom(A,B,D)
        flat_top(B,D,C)

    def __gl_triangle_bc(self, A : V3, B : V3, C : V3, verts = (), tex_coords = (), normals = (), clr = None):        
        min_x = round(min(A.x, B.x, C.x))
        min_y = round(min(A.y, B.y, C.y))
        max_x = round(max(A.x, B.x, C.x))
        max_y = round(max(A.y, B.y, C.y))
        
        triangle_normal = mf.cross( mf.subtract_V3(verts[1], verts[0]), mf.subtract_V3(verts[2], verts[0]))
        triangle_normal = mf.divition(triangle_normal, mf.norm(triangle_normal))
        
        for x in range(min_x, max_x + 1):
            for y in range(min_y, max_y + 1):
                u, v, w = bary_coords(A, B, C, V2(x, y))

                if 0<=u and 0<=v and 0<=w:

                    z = A.z * u + B.z * v + C.z * w

                    if 0<=x<self.width and 0<=y<self.height:
                        if z < self.zbuffer[x][y] and -1 <= z <= 1:
                            self.zbuffer[x][y] = z

                            if self.active_shader:
                                r, g, b = self.active_shader(
                                    self,
                                    bary_coords=(u,v,w),
                                    v_color = clr or self.current_color,
                                    tex_coords = tex_coords,
                                    normals = normals,
                                    triangle_normal = triangle_normal
                                )

                                self.gl_point(x, y, color(r,g,b))
                            else:
                                self.glPoint(x,y, clr)
        
    def render_background(self, filename : str) -> None:
        background = Texture(filename)        
        for x in range(self.width):
            for y in range(self.height):
                tex_color = background.get_color_for_background(x, y)
                if tex_color:
                    self.gl_point(x, y, color(tex_color[0], tex_color[1], tex_color[2]))
        
    def gl_finish(self, filename : str) -> None:
        word = lambda w : struct.pack('=h', w)
        dword = lambda d : struct.pack('=l', d)
        
        with open(filename, "wb") as file:
            #Header
            pixel = dword( 14 + 40 + (self.width * self.height * 3 )) # Multplicado por 3 porque cada pixel tiene 3 bytes
            header = [bytes('B'.encode('ascii')), bytes('M'.encode('ascii')), pixel, dword(0), dword(14 + 40)]
            for e_header in header: file.write(e_header)
    
            # Info Header
            info_header = [
                dword(40), dword(self.width), dword(self.height), word(1), word(24), dword(0), 
                dword(self.width * self.height * 3), dword(0), dword(0), dword(0), dword(0)
            ]
            for e_info_header in info_header: file.write(e_info_header)
            
            # Pintar toda la tabla
            for y in range(self.height):
                for x in range(self.width):                
                    file.write(self.pixels[x][y])
