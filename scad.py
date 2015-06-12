
import solid as sc

def rect2scad(rect, height, z_start = 0.0, mirrored = False):
    """
    Convert a Rectangle into an openscad cube
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
    def __init__(self, board_bbox, space_top=15.0, space_bot=15.0, board_thickness=1.6, thickness=10.0):
        self._space_top = space_top
        self._space_bot = space_bot
        self._thickness = thickness
        self._board_slot = 3.0  #Width of the slot that holds the board
        self._board_thickness = board_thickness
        self._board_bbox = board_bbox

        # From the side:
        # _ top of case
        # _ top of inner cavity
        # | space top
        # _ top of board
        # _ bottom of board (this is z=0)
        # | space_bot
        # _ bottom of inner cavity
        # _ bottom of case

        assert self._board_slot < self._thickness,"Can't make the board slot more than the thickness"

        #The inner empty cavity
        inner = sc.translate([board_bbox.left(), board_bbox.bot(), -self._space_bot])(
                    sc.cube([board_bbox.width, board_bbox.height, self.cavity_height])
        )
        outer_shell = sc.minkowski()(inner, sc.cube(self._thickness*2, center=True))
        self._case = outer_shell - inner

        slot = board_bbox.copy().pad(self._board_slot)
        self._case -= rect2scad(slot, self._board_thickness + 0.5)

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
        return self.cavity_height + self._thickness*2

    def cut_top(self, rect):
        """
        Cut a hole in the top of the case
        """
        self._case -= rect2scad(rect, self.cavity_height)

    def cut_bot(self, rect):
        """
        Cut a hole in the bottom of the case
        """
        self._case -= rect2scad(rect, self.cavity_height, mirrored=True)

    def save(self, file):
        # Add screws
        screw_head_radius = 3.0
        screw_head_length = 2.5
        screw_shaft_radius = 1.25
        screw_shaft_length = 12.0
        head = sc.translate([0,0,screw_shaft_length])(
                    sc.cylinder(h=screw_head_length + 0.1, r=screw_head_radius, segments=20)
                )
        shaft = sc.cylinder(h=screw_shaft_length + 0.1, r=screw_shaft_radius, segments=20)

        # Origin is top of screw
        screw = sc.rotate([0,90,0])(
                    sc.translate([0,0,-screw_shaft_length - screw_head_length])(
                        sc.union()(head,shaft)
                        )
                    )
        sc.scad_render_to_file(screw, "screw.scad", include_orig_code=False)

        # Place 4 screws in the right side
        #The coordinates for the screws
        ymin = self._board_bbox.bot() - self._thickness/2
        ymax = self._board_bbox.top() + self._thickness/2
        zmin = -self.cavity_bot - self._thickness/2
        zmax = self.cavity_top - self._thickness/2
        x = self._board_bbox.right() + self._thickness  # x is always the same

        #Top left
        for y in [ymin, ymax]:
            for z in [zmin, zmax]:
                self._case -= sc.translate([x,y,z])(screw)

        top_area = self._board_bbox.copy().pad(self._thickness*2)
        top_area = rect2scad(top_area, self._thickness + 0.1, self.cavity_top - 0.05)

        # Separate the sides to be screwed on
        main_area = self._board_bbox.copy()
        main_area.bounds[0][1] -= self._thickness*2
        main_area.bounds[1][1] += self._thickness*2
        main_area.bounds[1][0] -= 0.05    #So we don't have a degenerate face
        main_area.bounds[0][0] -= self._thickness*2
        main_area = rect2scad(main_area, self.height * 2, z_start = -self.height - 10)
        main_part = self._case * main_area
        side = self._case - (main_area + top_area)

        top = self._case * top_area
        main_part -= top_area
        sc.scad_render_to_file(top, "top." + file, include_orig_code=False)

        sc.scad_render_to_file(main_part, "main." + file, include_orig_code=False)
        sc.scad_render_to_file(side, "side." + file, include_orig_code=False)

        exploded = sc.union()(
            main_part,
            sc.translate([40,0,0])(side),
            sc.translate([0,0,40])(top)
        )
        sc.scad_render_to_file(exploded, "exploded." + file)
        sc.scad_render_to_file(self._case, file, include_orig_code=False)

