
import solid as sc
from Rectangle import Rectangle
import numpy as np

def rect2scad(rect, height, z_start = 0.0, mirrored = False):
    """
    Convert a Rectangle into an openscad cube by giving it a height and Z start
    """
    scad_cube = sc.translate([rect.left(), rect.bot(), z_start])(
        sc.cube([rect.width, rect.height, height])
    )
    if mirrored:
        return sc.scale([1,1,-1])(scad_cube)
    else:
        return scad_cube




class ScadCase(object):
    """
    A wrapper around OpenSCAD objects
    Allows for easier geometric operations on a case, such as
    cutting holes in the top, bottom, or sides
    """
    def __init__(self, board_bbox,
                 space_top=15.0,
                 space_bot=15.0,
                 board_thickness=1.6,
                 thickness_z = 4.0,
                 thickness_sides = 6.7):
        self._space_top = space_top
        self._space_bot = space_bot
        self._thickness_xy = thickness_sides    # thickness of each side
        self._thickness_z = thickness_z         # thickness of top and bottom
        self._board_slot = 3.5  #Width of the slot that holds the board
        self._board_thickness = board_thickness
        self._board_bbox = board_bbox.copy().pad(-self._board_slot)

        # From the side:
        # _ top of case
        # _ top of inner cavity
        # | space top
        # _ top of board
        # _ bottom of board (this is z=0)
        # | space_bot
        # _ bottom of inner cavity
        # _ bottom of case

        assert self._board_slot < self._thickness_xy, "Can't make the board slot more than the thickness of the sides"

        #The inner empty cavity
        inner = rect2scad(self._board_bbox, height=self.cavity_height, z_start = -self._space_bot)

        padded = self._board_bbox.copy().pad(self._thickness_xy)
        outer = rect2scad(padded,
                          height=self.cavity_height + self._thickness_z*2,
                          z_start=-(self._space_bot + self._thickness_z))

        self._case = outer - inner
        slot = self._board_bbox.copy().pad(self._board_slot)
        assert slot.area() < padded.area()
        self._case -= rect2scad(slot, self.cavity_top + 0.05)

    @property
    def cavity_height(self):
        """
        The height of the empty space inside the case
        """
        return self._space_top + self._space_bot + self._board_thickness

    @property
    def cavity_top(self):
        """
        Distance from z=0 to the top of the inner cavity
        """
        return self._board_thickness + self._space_top

    @property
    def cavity_bot(self):
        """
        Distance from z=0 to the bottom of cavity
        """
        return self._space_bot

    @property
    def height(self):
        return self.cavity_height + self._thickness_z*2

    def cut_top(self, rect):
        """
        Cut a hole in the top of the case
        """
        self._case -= rect2scad(rect, self.cavity_height + self._thickness_z*2)

    def cut_bot(self, rect):
        """
        Cut a hole in the bottom of the case
        """
        self._case -= rect2scad(rect, self.cavity_height + self._thickness_z*2, mirrored=True)

    def cut_side_top(self, rect):
        """
        Cut a hole in the side of the case above the board
        """
        cut = self._make_cutout_rect(rect)
        self._case -= rect2scad(cut, self.cavity_top - self._board_thickness, self._board_thickness)


    def save(self, file):
        # Add screws
        screw_head_radius = 3.0
        screw_head_length = 2.5
        screw_shaft_radius = 1.30
        screw_shaft_length = 15.0
        head = sc.translate([0,0,screw_shaft_length])(
                    sc.cylinder(h=screw_head_length + 100, r=screw_head_radius, segments=20)
                )
        shaft = sc.cylinder(h=screw_shaft_length + 0.1, r=screw_shaft_radius, segments=20)
        screw_down = sc.translate([0,0,-screw_shaft_length - screw_head_length])(
                        sc.union()(head,shaft)
                    )

        # Origin is top of screw
        screw_side = sc.rotate([0,90,0])(screw_down)
        sc.scad_render_to_file(screw_side, "screw.scad", include_orig_code=False)

        # Place 4 screws in the right side
        screw_recess_side = 1.0
        assert screw_recess_side < self._thickness_xy
        side_thick = self._thickness_xy - self._board_slot
        ymin = self._board_bbox.bot() - self._board_slot - side_thick/2.0
        ymax = self._board_bbox.top() + self._board_slot + side_thick/2.0
        zmin = -self.cavity_bot - self._thickness_z + screw_head_radius
        zmax = self.cavity_top - self._thickness_z - screw_head_radius
        x = self._board_bbox.right() + self._thickness_xy + 1.0

        # Add screws to the side
        for y in [ymin, ymax]:
            for z in [zmin, zmax]:
                self._case -= sc.translate([x,y,z])(screw_side)

        # Add screws to the top
        screw_recess_top = 0
        assert screw_recess_top < self._thickness_z
        min_screw_depth = 3.0

        #Lowest depth screw can possibly go
        zmin = self.cavity_top + screw_head_length + min_screw_depth
        z_want = self.cavity_top + self._thickness_z - screw_recess_top
        z = max(zmin, z_want)

        ys = [self._board_bbox.top() + self._board_slot + (self._thickness_xy - self._board_slot)/2.0,
              self._board_bbox.bot() - self._board_slot - (self._thickness_xy - self._board_slot)/2.0]
        xs = [self._board_bbox.left() + screw_head_radius, self._board_bbox.right() - screw_shaft_length - 1.0]
        for y in ys:
            for x in xs:
                self._case -= sc.translate([x,y,z])(screw_down)


        #Add screws to hold down the board
        # x = self._board_bbox.left() + (self._board_bbox.width + self._board_slot*2)/2.0

        top_area_select = self._board_bbox.copy().pad(self._thickness_xy*2)
        top_area_select = rect2scad(top_area_select, self._thickness_z + 0.1, self.cavity_top - 0.05)

        # Separate the sides to be screwed on
        # main_area is the case without the top or side
        main_area = self._board_bbox.copy()
        main_area.bounds[0][0] -= self._thickness_xy*2
        main_area.bounds[0][1] -= self._thickness_xy*2
        main_area.bounds[1][0] -= 0.05    #So we don't have a degenerate face
        main_area.bounds[1][1] += self._thickness_xy*2
        main_area = rect2scad(main_area, self.height * 2, z_start = -self.height - 10)
        main_part = self._case * main_area
        side = self._case - (main_area + top_area_select)      # Side of the case, first part to screw on

        #The top of the case (screwed on after the side)
        top = self._case * top_area_select
        main_part -= top_area_select
        sc.scad_render_to_file(top, "top." + file, include_orig_code=False)

        sc.scad_render_to_file(main_part, "main." + file, include_orig_code=False)
        sc.scad_render_to_file(side, "side." + file, include_orig_code=False)

        exploded = sc.union()(
            main_part,
            sc.translate([40,0,0])(side),
            sc.translate([0,0,40])(top)
        )
        sc.scad_render_to_file(exploded, "exploded." + file, include_orig_code=False)
        sc.scad_render_to_file(self._case, file, include_orig_code=False)

    def _make_cutout_rect(self, rect):
        """
        If rect intersects container, return a rectangle to cut out the container on the side
        """
        if self._board_bbox.encloses(rect):
            return None

        cut = rect
        for axis in xrange(2):
            if rect.low(axis) < self._board_bbox.low(axis):    #left/bottom cut
                move = np.array([0,0])
                move[axis] = -self._thickness_xy*2
                cut = Rectangle.union(cut, rect.copy().move(move))
                # print cut
            if rect.high(axis) > self._board_bbox.high(axis):  #right/top cut
                move = np.array([0,0])
                move[axis] = self._thickness_xy*2
                cut = Rectangle.union(cut, rect.copy().move(move))
                # print cut
        return cut

