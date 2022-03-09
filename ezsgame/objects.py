import pygame as pg, random
from ezsgame.premade import *
from pathfinding.core.diagonal_movement import DiagonalMovement
from pathfinding.core import grid
from pathfinding.finder.a_star import AStarFinder

pg.init()

class IObject(Object):
    def __init__(self,  pos, size, screen, **styles):
        super().__init__(pos, size, **styles)
        if screen == None:
            raise Exception(f"IObject object needs screen (ID : {self._id})")
        self.screen = screen
        self.objects = Group()
        self._clicked = False
        
    @property
    def clicked(self):
        return self._clicked
    @clicked.setter
    def clicked(self, value):
        self._clicked = value
        
    def _process_click(self, func, *args, **kwargs):
        def inner(*args, **kwargs):
            self.clicked = True
            func(*args, **kwargs)
        return inner

    def click(self, *args, **kwargs):
        def wrapper(func):
            func = self._process_click(func, *args, **kwargs)
            self.screen.events.add_event_listener("click", self, func)                
                    
        return wrapper
    
    def hover(self, *args, **kwargs):
        def wrapper(func):
            self.screen.events.add_event_listener("hover", self, func)
        return wrapper

    def unhover(self, *args, **kwargs):
        def wrapper(func):
            self.screen.events.add_event_listener("unhover", self, func)
        return wrapper
    
    def _process_unclick(self, func, *args, **kwargs):
        def inner(*args, **kwargs):
            if self.clicked:
                func(*args, **kwargs)
                self.clicked = False
            
        return inner
    
    def unclick(self, *args, **kwargs):
        def wrapper(func):
            func = self._process_unclick(func, *args, **kwargs)
            self.screen.events.on("mouseup", func)
        return wrapper
    
    def add(self, objects):
        if type(objects) == list:
            for object in objects:
                object.pos = [object.pos[0] + self.pos[0], object.pos[1] + self.pos[1]]
                self.objects.add(object)
        else:
            objects.pos = [objects.pos[0] + self.pos[0], objects.pos[1] + self.pos[1]]
            self.objects.add(objects)            
            
    def remove(self, object):
        self.objects.remove(object)

class IRect(IObject):
    def __init__(self, pos, size, screen, **styles):
        super().__init__(pos, size, screen, **styles)
        
    def draw(self, screen=None):
        screen = self.screen if screen == None else screen
        pg.draw.rect(screen.surface, self.color, [*self.get_pos(screen), *self.size], int(self.stroke))

class ICircle(IObject, Circle):
    def __init__(self, pos, radius, screen, **styles):
        size = [radius*2, radius*2]
        IObject.__init__(self, pos, size, screen, **styles)
        Circle.__init__(self, pos, radius, **styles)
        
class Grid(Object):
    def __init__(self, pos, size, grid_size, screen, **styles):
        super().__init__(pos, size, **styles)
        self.box_color = styles.get("box_color", "white")
        self.screen = screen
        self.grid_size = grid_size
        self.matrix = self.grid_div(*self.grid_size) 
        self.grid = self.grid_split(self.matrix, self.grid_size[1])
        self.colors_grid = [[obj.color for obj in row] for row in self.grid]
          
    def div(self, axis, q):
        r'''
        Return list of division points of the screen -> [[x1, x2], [x1, x2], ...]
        '''
        divs = []
        if axis == "x":
            # should append [start, end] for each division
            for i in range(q):
                divs.append([round(i * self.size[0] / q, 1), round((i + 1) * self.size[0] / q, 1)])
        elif axis == "y":
            # should append [start, end] for each division
            for i in range(q):
                divs.append([round(i * self.size[1] / q, 1), round((i + 1) * self.size[1] / q, 1)])
            
        return divs
        
    def grid_div(self, cols=3, rows=3, transpose=False):
        r'''
        Returns the division of the screen into a grid -> [[x, y, w, h], [x, y, w, h], ...]
        '''
        grid = []
        divs_x = self.div("x", cols)
        box_width = divs_x[-1][0] - divs_x[-2][0]
        divs_y = self.div("y", rows)
        box_height = divs_y[-1][0] - divs_y[-2][0]
        self.grid_size = [rows, cols]
        
        for i in range(cols):
            for j in range(rows):
                if transpose:
                    grid.append([divs_x[j][0], divs_y[i][0], box_width, box_height])
                else:
                    grid.append([divs_x[i][0], divs_y[j][0], box_width, box_height])
        self.grid_space = len(grid)
        self.grid_box_size = [box_width, box_height]
        return grid
    
    def grid_split(self, matrix, grid_size):
        r'''
        Splits a matrix into a grid : [1,2,3,4,5,6,7,8,9] -> [[Unit,Unit,Unit], [Unit,Unit,Unit], [Unit,Unit,Unit]]
        '''
        if isinstance(grid_size, list) or isinstance(grid_size, tuple):
            grid_size = grid_size[1]
        
        grid = [matrix[i:i+grid_size] for i in range(0, len(matrix), grid_size)]
        return [[Unit(pos=i[:2], size=i[2:], color=self.box_color)  for i in row] for row in grid]
    
    def draw(self, screen=None):
        screen = self.screen if screen == None else screen
        
        pg.draw.rect(screen.surface, self.color, [*self.get_pos(screen), *self.size], int(self.stroke))
        for row in self.grid:
            for obj in row:
                obj.draw(screen)
            
    def highlight_current(self, color="red"):
        for i in range(len(self.colors_grid)):
            for j in range(len(self.colors_grid[i])):
                if self.colors_grid[i][j] != color:
                    self.grid[i][j].color = self.colors_grid[i][j]
        
        mouse_pos = self.screen.mouse_pos()
        pos = int(mouse_pos[0] // self.grid_box_size[0]), int(mouse_pos[1] // self.grid_box_size[1])
        # select the current box
        
        if pos[0] < self.grid_size[0] and pos[1] < self.grid_size[1]:
            self.grid[pos[0]][pos[1]].color = color

    def get_path(self, start,end):
        int_grid = [[1 for x in j] for j in self.grid]
    
        _grid = grid.Grid(matrix=int_grid)
        start = _grid.node(*start)
        end = _grid.node(*end)

        finder = AStarFinder(diagonal_movement=DiagonalMovement.always)

        path, runs = finder.find_path(start=start, end=end, grid=_grid)
        
        return path

    def highlight_path(self, start, end, color="red"):
        if  0 > (start[0] or start[1]) or start[1] > self.grid_size[1] or start[0] > self.grid_size[0]:
            raise Exception("Start position is out of bounds")
        if 0 > (end[0] or end[1]) or end[1] > self.grid_size[1] or end[0] > self.grid_size[0]:
            raise Exception("End position is out of bounds")
        if start == end:
            raise Exception("Start and end positions must be different")
        
        path = self.get_path(start, end)
        for i in range(len(path)):
            self.grid[path[i][0]][path[i][1]].color = color
    

    def get_current(self):
        mouse_pos = self.screen.mouse_pos()
        pos = int(mouse_pos[0] // self.grid_box_size[0]), int(mouse_pos[1] // self.grid_box_size[1])
        # select the current box
        if pos[0] < self.grid_size[0] and pos[1] < self.grid_size[1]:
            return self.grid[pos[0]][pos[1]]
        else:
            return None

class Group:
    def __init__(self, objects=[], screen=None):
        if isinstance(objects, list):
            self.objects = objects
        else:
            self.objects = [objects]
        if screen != None:
            self.screen = screen
            
    def add(self, objs):
        if type(objs) == list:
            self.objects += objs
        else:
            self.objects.append(objs)    

    def remove(self, obj):
        self.objects.remove(obj)
    
    def draw(self, screen=None):
        screen = self.screen if screen == None else screen
        if screen == None:
            raise Exception("Screen is not set, need screen to draw")
        
        for obj in self.objects:
            obj.draw(screen)

def _get_object(object):
    args = {k:v for k,v in object.items() if k != "type" and  k != "elements"}
    try:
        obj = eval(object["type"].capitalize())(**args)
    except Exception as e:
        raise Exception("Could not load object: " + str(e))
                
    return obj

def _get_object_child(parent, object, childs=[]):
    for key,value in object["elements"].items():
        if "pos" in value:
            value["pos"] = [value["pos"][0] + parent.pos[0], value["pos"][1] + parent.pos[1]]
        
        parent = _get_object(value)
        childs.append(parent)
   
    for value in object["elements"].values():
        if "elements" in value:   
            _get_object_child(parent, value, childs)
    
    return childs
    
def load_custom_object(object):
    r'''
    Load a custom object from a object of json file
    '''
    obj = Group(_get_object(object))   
    obj.add(_get_object_child(obj.objects[0], object))
    return obj

class RangeBar(Object):
    def __init__(self, pos, size, min, max, value, screen, **styles):
        for item in (min, max, value):
            if item < 0 or item > 100:
                raise ValueError(f"{item} must be between 0 and 100, at RangeBar object")
        
        super().__init__(pos=pos, size=size, screen=screen, **styles)
        
        radius = styles.get("radius", self.size[1] / 2.5 - self.size[1]//8)
        wheel_color = styles.get("wheel_color", "white")
        
        self.wheel = ICircle(pos=[0,0], radius=radius, color=wheel_color, screen=self.screen)
        self.bar = Object(pos=pos, size=size, **styles)
        
        self.min = (min  * (self.pos[0]+ self.size[0])) / 100 if min != 0 else self.pos[0]
        self.max = (max * (self.pos[0]+ self.size[0])) / 100
        self.value = (value * (self.min + self.max)) / 100
        self.screen = screen        
        
        self._evname = f"RangeBar_{self._id}_update_value_[{random.randint(0,255)}]"
        
        @self.wheel.click()    
        def wheel_click():     
            self._evname = f"RangeBar_{self._id}_update_value_[{random.randint(0,255)}]"
            self.screen.time.add(time=10, callback=lambda: self._update_value(), name=self._evname) 

        @self.wheel.unclick()
        def wheel_unclick():
            if self.wheel.clicked:
                self.screen.time.remove(name=self._evname)
                self.wheel.color = "white"

    def _update_value(self):
        mouse_pos = self.screen.mouse_pos()[0]
 
        if mouse_pos + self.wheel.radius < self.min:
            self.value = self.min 
        
        elif mouse_pos + self.wheel.size[0] > self.max:
            self.value = self.max
            
        else:
            self.value = mouse_pos 
            
        self.wheel.color = "red"

    def _calculate_wheel_pos(self):
        x = self.value
        if x == self.min:
            x = self.min - self.wheel.radius /2 
            
        elif x == self.max: 
            x = self.max + self.wheel.radius /2
                        
        self.wheel.pos = [x, self.pos[1]+self.size[1]//2]

    def draw(self, screen=None):
        screen = self.screen if screen == None else screen

        self._calculate_wheel_pos()
        Rect(pos=[self.pos[0], self.pos[1]+self.size[1]/2], size=[self.size[0]+self.wheel.radius, self.size[1]//8], color=self.color, screen=self.screen).draw()
        self.wheel.draw(screen)
    
    def get_percent(self):
        if self.value == self.min:
            return 0
        elif self.value == self.max:
            return 100
        
        return round( (self.value / ( (self.min + self.wheel.radius) + (self.max - self.wheel.radius) ) ) * 100, 4)
    
        


def distance_between(screen, a, b):
    # return the distance between two points in boxes, box size is screen.unit_size
    
    y_len = screen.size[1] // screen.unit_size[1]
    x_len = screen.size[0] // screen.unit_size[0]
    
    a_pos = a.get_pos(screen) + [a.size[0]//2, a.size[1]//2]
    b_pos = b.get_pos(screen) + [b.size[0]//2, b.size[1]//2]
    
    matrix = [[] for i in range(y_len)]
    
    for row in range(y_len):
        for col in range(x_len):
            matrix[row].append(0)
            
    