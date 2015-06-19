#!/usr/bin/env python

import argparse
import Swoop.ext.Geometry as SwoopGeom
import Swoop
from solid import *
import numpy as np
from Rectangle import Rectangle
from lxml import etree as ET
import math
import scad



def vertical_cuts(container_rect, cuts, space_top, thickness, mirrored = False):
    assert thickness > 0
    assert space_top > 0
    cut_through_roof = space_top + thickness + 30
    for rect in cuts:
        yield rect2scad(rect, cut_through_roof, mirrored=mirrored) #top
        padded_cut = rect.copy().pad(1.0)
        if not container_rect.encloses(padded_cut):  #faceplate sticks out the side
            # print "side cut {0}".format(rect.eagle_code())
            cut = make_cutout_rect(container_rect, padded_cut, CASE_THICKNESS)
            if cut is not None:
                yield rect2scad(cut, space_top, mirrored=mirrored)

parser = argparse.ArgumentParser(description="Make 3D printed cases for your gadgets")
parser.add_argument("brdfile", help="Board file to make a case from")
parser.add_argument("-f","--file", help="SCAD output file", default="out.scad")
parser.add_argument("-g","--gspec",help="gspec file containing height information")
parser.add_argument("--open", action="store_true", help="The top of the case is open")
args = parser.parse_args()

board = SwoopGeom.from_file(args.brdfile)

#Find the bounding box of the board
board_box = board.get_bounding_box()

top = 15.0
bottom = 15.0

if args.gspec is not None:
    gspec = ET.parse(args.gspec)
    for option in gspec.findall("option"):
        if option.get("name")=="front-standoff-height":
            top = float(option.attrib["value"])
        elif option.get("name")=="back-standoff-height":
            bottom = float(option.attrib["value"])

case = scad.ScadCase(board_box, space_top=top, space_bot=bottom)


tfaceplate_filter = lambda p: hasattr(p,"layer") and p.get_layer()=="tFaceplate"
bfaceplate_filter = lambda p: hasattr(p,"layer") and p.get_layer()=="bFaceplate"


#Swap the layers if mirrored
for elem in board.get_elements():
    if elem.get_mirrored():
        for child in elem.get_package_moved().get_children():
            if tfaceplate_filter(child):
                child.set_layer("bFaceplate")
            elif bfaceplate_filter(child):
                child.set_layer("tFaceplate")


#Subtract out all the top faceplate stuff
tfaceplate = board.get_elements().\
    get_package_moved().\
    get_children().\
    filtered_by(tfaceplate_filter).\
    get_bounding_box()
tfaceplate += board.get_plain_elements().filtered_by(tfaceplate_filter).get_bounding_box()

#And bottom faceplate
bfaceplate = board.\
    get_elements().\
    get_package_moved().\
    get_children().\
    filtered_by(bfaceplate_filter).\
    get_bounding_box()
bfaceplate += board.get_plain_elements().filtered_by(bfaceplate_filter).get_bounding_box()

for rect in tfaceplate:
    case.cut_top(rect)
for rect in bfaceplate:
    case.cut_bot(rect)


side_cuts = board.get_plain_elements().\
    filtered_by(lambda p: hasattr(p,"layer") and p.layer=="tSideCut").\
    get_bounding_box()
for cut in side_cuts:
    case.cut_side_top(cut)


case.save(args.file)

