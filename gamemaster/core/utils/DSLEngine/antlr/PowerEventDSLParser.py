"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

# Generated from gamemaster/core/utils/DSLEngine/antlr/PowerEventDSL.g4 by ANTLR 4.13.2
# encoding: utf-8
from antlr4 import *
from io import StringIO
import sys
if sys.version_info[1] > 5:
	from typing import TextIO
else:
	from typing.io import TextIO

def serializedATN():
    return [
        4,1,123,745,2,0,7,0,2,1,7,1,2,2,7,2,2,3,7,3,2,4,7,4,2,5,7,5,2,6,
        7,6,2,7,7,7,2,8,7,8,2,9,7,9,2,10,7,10,2,11,7,11,2,12,7,12,2,13,7,
        13,2,14,7,14,2,15,7,15,2,16,7,16,2,17,7,17,2,18,7,18,2,19,7,19,2,
        20,7,20,2,21,7,21,2,22,7,22,2,23,7,23,2,24,7,24,2,25,7,25,2,26,7,
        26,2,27,7,27,2,28,7,28,2,29,7,29,2,30,7,30,2,31,7,31,2,32,7,32,2,
        33,7,33,2,34,7,34,2,35,7,35,2,36,7,36,2,37,7,37,2,38,7,38,2,39,7,
        39,2,40,7,40,2,41,7,41,2,42,7,42,2,43,7,43,2,44,7,44,2,45,7,45,2,
        46,7,46,2,47,7,47,2,48,7,48,2,49,7,49,2,50,7,50,2,51,7,51,2,52,7,
        52,2,53,7,53,2,54,7,54,2,55,7,55,2,56,7,56,2,57,7,57,2,58,7,58,2,
        59,7,59,2,60,7,60,2,61,7,61,2,62,7,62,2,63,7,63,2,64,7,64,2,65,7,
        65,2,66,7,66,2,67,7,67,2,68,7,68,2,69,7,69,2,70,7,70,2,71,7,71,2,
        72,7,72,2,73,7,73,2,74,7,74,2,75,7,75,2,76,7,76,2,77,7,77,2,78,7,
        78,2,79,7,79,2,80,7,80,2,81,7,81,2,82,7,82,2,83,7,83,2,84,7,84,1,
        0,5,0,172,8,0,10,0,12,0,175,9,0,1,0,1,0,1,1,1,1,1,1,1,1,3,1,183,
        8,1,1,2,1,2,1,2,1,2,3,2,189,8,2,1,2,1,2,1,2,5,2,194,8,2,10,2,12,
        2,197,9,2,1,2,1,2,1,3,1,3,1,3,5,3,204,8,3,10,3,12,3,207,9,3,1,4,
        1,4,1,4,1,4,1,4,1,4,1,4,1,5,1,5,1,5,1,5,1,5,1,5,1,5,1,6,1,6,1,6,
        1,6,3,6,227,8,6,1,6,1,6,3,6,231,8,6,1,6,1,6,1,6,1,6,1,6,1,6,1,6,
        3,6,240,8,6,1,6,1,6,1,6,1,6,1,6,1,6,1,6,1,6,1,6,3,6,251,8,6,1,6,
        1,6,3,6,255,8,6,1,7,1,7,1,7,1,7,1,7,3,7,262,8,7,1,7,1,7,1,7,1,7,
        1,7,1,7,1,7,3,7,271,8,7,1,7,1,7,1,7,1,7,1,7,1,7,1,7,1,7,1,7,3,7,
        282,8,7,1,7,1,7,3,7,286,8,7,1,8,1,8,1,8,1,9,1,9,1,9,3,9,294,8,9,
        1,10,1,10,1,10,3,10,299,8,10,1,10,1,10,1,11,1,11,1,11,1,11,1,11,
        1,12,1,12,1,12,5,12,311,8,12,10,12,12,12,314,9,12,1,13,1,13,3,13,
        318,8,13,1,13,1,13,1,14,1,14,1,14,1,14,3,14,326,8,14,1,15,1,15,1,
        15,1,15,1,15,1,15,1,15,1,15,1,15,1,15,3,15,338,8,15,1,16,1,16,1,
        16,1,17,1,17,1,17,1,17,1,18,1,18,1,18,1,18,1,19,1,19,1,19,1,19,1,
        19,1,19,1,19,3,19,358,8,19,1,20,1,20,1,20,1,20,1,20,1,20,1,20,3,
        20,367,8,20,1,21,1,21,1,21,1,21,1,21,3,21,374,8,21,1,22,1,22,1,22,
        1,22,1,22,3,22,381,8,22,1,23,1,23,1,23,1,23,1,23,1,24,1,24,1,24,
        1,24,1,24,1,25,1,25,1,25,1,25,1,25,1,25,3,25,399,8,25,1,25,3,25,
        402,8,25,1,25,1,25,5,25,406,8,25,10,25,12,25,409,9,25,1,26,1,26,
        1,26,5,26,414,8,26,10,26,12,26,417,9,26,1,27,1,27,1,27,5,27,422,
        8,27,10,27,12,27,425,9,27,1,28,1,28,1,28,3,28,430,8,28,1,29,1,29,
        1,29,1,29,1,29,1,29,1,30,1,30,1,30,1,31,1,31,1,31,1,32,1,32,1,32,
        1,32,1,32,1,32,1,32,1,32,1,32,1,32,1,32,3,32,455,8,32,1,33,1,33,
        1,33,1,34,1,34,1,34,1,34,3,34,464,8,34,1,35,1,35,1,35,1,36,1,36,
        1,36,3,36,472,8,36,1,36,1,36,1,36,1,36,1,36,1,36,1,36,1,36,1,36,
        1,36,3,36,484,8,36,1,37,1,37,3,37,488,8,37,1,37,1,37,1,37,1,37,1,
        37,1,38,1,38,3,38,497,8,38,1,38,1,38,3,38,501,8,38,1,39,1,39,3,39,
        505,8,39,1,39,1,39,1,39,1,40,1,40,3,40,512,8,40,1,40,1,40,3,40,516,
        8,40,1,41,1,41,1,41,1,42,1,42,1,43,1,43,1,43,1,43,3,43,527,8,43,
        1,44,1,44,1,44,1,44,5,44,533,8,44,10,44,12,44,536,9,44,1,44,1,44,
        1,45,1,45,1,46,1,46,3,46,544,8,46,1,46,1,46,1,47,1,47,1,47,1,47,
        1,48,1,48,1,49,1,49,3,49,556,8,49,1,49,1,49,1,49,1,50,1,50,1,51,
        3,51,564,8,51,1,51,1,51,1,52,1,52,1,53,1,53,1,54,1,54,1,54,3,54,
        575,8,54,1,55,1,55,1,55,1,55,1,55,1,56,1,56,1,56,1,56,1,56,1,56,
        1,56,1,57,1,57,1,57,1,57,1,57,3,57,594,8,57,1,57,1,57,1,57,1,58,
        1,58,1,59,1,59,1,59,1,60,1,60,1,61,1,61,3,61,608,8,61,1,62,1,62,
        1,62,3,62,613,8,62,1,63,1,63,1,63,3,63,618,8,63,1,64,1,64,1,64,1,
        64,1,64,1,64,1,64,1,64,3,64,628,8,64,1,65,1,65,3,65,632,8,65,1,66,
        1,66,3,66,636,8,66,1,67,1,67,1,67,1,68,1,68,1,68,1,68,1,68,1,68,
        1,68,1,68,3,68,649,8,68,1,69,1,69,1,70,1,70,1,71,1,71,1,72,1,72,
        1,72,5,72,660,8,72,10,72,12,72,663,9,72,1,73,1,73,1,73,5,73,668,
        8,73,10,73,12,73,671,9,73,1,74,1,74,1,74,1,74,1,74,3,74,678,8,74,
        1,75,1,75,3,75,682,8,75,1,76,1,76,1,76,1,76,1,77,1,77,1,77,5,77,
        691,8,77,10,77,12,77,694,9,77,1,78,1,78,1,78,5,78,699,8,78,10,78,
        12,78,702,9,78,1,79,1,79,1,79,1,79,1,79,1,79,3,79,710,8,79,1,80,
        1,80,3,80,714,8,80,1,81,1,81,1,82,1,82,1,83,1,83,1,83,1,83,1,83,
        1,83,1,83,1,83,1,83,1,83,1,83,1,83,1,83,1,83,1,83,1,83,1,83,1,83,
        1,83,1,83,1,83,3,83,741,8,83,1,84,1,84,1,84,0,0,85,0,2,4,6,8,10,
        12,14,16,18,20,22,24,26,28,30,32,34,36,38,40,42,44,46,48,50,52,54,
        56,58,60,62,64,66,68,70,72,74,76,78,80,82,84,86,88,90,92,94,96,98,
        100,102,104,106,108,110,112,114,116,118,120,122,124,126,128,130,
        132,134,136,138,140,142,144,146,148,150,152,154,156,158,160,162,
        164,166,168,0,13,1,0,23,24,1,0,27,28,4,0,25,26,29,29,31,31,58,70,
        1,0,75,78,1,0,79,80,1,0,120,121,2,0,118,118,121,121,1,0,85,90,2,
        0,94,94,120,120,1,0,97,98,1,0,99,104,1,0,105,106,1,0,113,117,750,
        0,173,1,0,0,0,2,182,1,0,0,0,4,184,1,0,0,0,6,200,1,0,0,0,8,208,1,
        0,0,0,10,215,1,0,0,0,12,254,1,0,0,0,14,285,1,0,0,0,16,287,1,0,0,
        0,18,293,1,0,0,0,20,295,1,0,0,0,22,302,1,0,0,0,24,307,1,0,0,0,26,
        317,1,0,0,0,28,325,1,0,0,0,30,337,1,0,0,0,32,339,1,0,0,0,34,342,
        1,0,0,0,36,346,1,0,0,0,38,350,1,0,0,0,40,359,1,0,0,0,42,368,1,0,
        0,0,44,375,1,0,0,0,46,382,1,0,0,0,48,387,1,0,0,0,50,392,1,0,0,0,
        52,410,1,0,0,0,54,418,1,0,0,0,56,429,1,0,0,0,58,431,1,0,0,0,60,437,
        1,0,0,0,62,440,1,0,0,0,64,454,1,0,0,0,66,456,1,0,0,0,68,463,1,0,
        0,0,70,465,1,0,0,0,72,483,1,0,0,0,74,487,1,0,0,0,76,496,1,0,0,0,
        78,504,1,0,0,0,80,511,1,0,0,0,82,517,1,0,0,0,84,520,1,0,0,0,86,526,
        1,0,0,0,88,528,1,0,0,0,90,539,1,0,0,0,92,541,1,0,0,0,94,547,1,0,
        0,0,96,551,1,0,0,0,98,555,1,0,0,0,100,560,1,0,0,0,102,563,1,0,0,
        0,104,567,1,0,0,0,106,569,1,0,0,0,108,574,1,0,0,0,110,576,1,0,0,
        0,112,581,1,0,0,0,114,588,1,0,0,0,116,598,1,0,0,0,118,600,1,0,0,
        0,120,603,1,0,0,0,122,607,1,0,0,0,124,612,1,0,0,0,126,614,1,0,0,
        0,128,619,1,0,0,0,130,631,1,0,0,0,132,635,1,0,0,0,134,637,1,0,0,
        0,136,640,1,0,0,0,138,650,1,0,0,0,140,652,1,0,0,0,142,654,1,0,0,
        0,144,656,1,0,0,0,146,664,1,0,0,0,148,677,1,0,0,0,150,681,1,0,0,
        0,152,683,1,0,0,0,154,687,1,0,0,0,156,695,1,0,0,0,158,709,1,0,0,
        0,160,711,1,0,0,0,162,715,1,0,0,0,164,717,1,0,0,0,166,740,1,0,0,
        0,168,742,1,0,0,0,170,172,3,2,1,0,171,170,1,0,0,0,172,175,1,0,0,
        0,173,171,1,0,0,0,173,174,1,0,0,0,174,176,1,0,0,0,175,173,1,0,0,
        0,176,177,5,0,0,1,177,1,1,0,0,0,178,183,3,8,4,0,179,183,3,10,5,0,
        180,183,3,4,2,0,181,183,3,12,6,0,182,178,1,0,0,0,182,179,1,0,0,0,
        182,180,1,0,0,0,182,181,1,0,0,0,183,3,1,0,0,0,184,185,5,1,0,0,185,
        186,5,121,0,0,186,188,5,2,0,0,187,189,3,6,3,0,188,187,1,0,0,0,188,
        189,1,0,0,0,189,190,1,0,0,0,190,191,5,3,0,0,191,195,5,4,0,0,192,
        194,3,14,7,0,193,192,1,0,0,0,194,197,1,0,0,0,195,193,1,0,0,0,195,
        196,1,0,0,0,196,198,1,0,0,0,197,195,1,0,0,0,198,199,5,5,0,0,199,
        5,1,0,0,0,200,205,5,121,0,0,201,202,5,6,0,0,202,204,5,121,0,0,203,
        201,1,0,0,0,204,207,1,0,0,0,205,203,1,0,0,0,205,206,1,0,0,0,206,
        7,1,0,0,0,207,205,1,0,0,0,208,209,5,7,0,0,209,210,5,8,0,0,210,211,
        5,9,0,0,211,212,5,10,0,0,212,213,3,118,59,0,213,214,5,11,0,0,214,
        9,1,0,0,0,215,216,5,7,0,0,216,217,5,12,0,0,217,218,5,13,0,0,218,
        219,5,10,0,0,219,220,3,118,59,0,220,221,5,11,0,0,221,11,1,0,0,0,
        222,223,5,14,0,0,223,224,3,122,61,0,224,225,5,6,0,0,225,227,1,0,
        0,0,226,222,1,0,0,0,226,227,1,0,0,0,227,228,1,0,0,0,228,230,3,18,
        9,0,229,231,3,16,8,0,230,229,1,0,0,0,230,231,1,0,0,0,231,232,1,0,
        0,0,232,233,5,11,0,0,233,255,1,0,0,0,234,235,5,15,0,0,235,236,3,
        140,70,0,236,237,5,6,0,0,237,239,3,18,9,0,238,240,3,16,8,0,239,238,
        1,0,0,0,239,240,1,0,0,0,240,241,1,0,0,0,241,242,5,11,0,0,242,255,
        1,0,0,0,243,244,5,16,0,0,244,245,3,104,52,0,245,246,5,17,0,0,246,
        247,5,18,0,0,247,248,5,6,0,0,248,250,3,18,9,0,249,251,3,16,8,0,250,
        249,1,0,0,0,250,251,1,0,0,0,251,252,1,0,0,0,252,253,5,11,0,0,253,
        255,1,0,0,0,254,226,1,0,0,0,254,234,1,0,0,0,254,243,1,0,0,0,255,
        13,1,0,0,0,256,257,5,14,0,0,257,258,3,130,65,0,258,259,5,6,0,0,259,
        261,3,18,9,0,260,262,3,16,8,0,261,260,1,0,0,0,261,262,1,0,0,0,262,
        263,1,0,0,0,263,264,5,11,0,0,264,286,1,0,0,0,265,266,5,15,0,0,266,
        267,3,140,70,0,267,268,5,6,0,0,268,270,3,18,9,0,269,271,3,16,8,0,
        270,269,1,0,0,0,270,271,1,0,0,0,271,272,1,0,0,0,272,273,5,11,0,0,
        273,286,1,0,0,0,274,275,5,16,0,0,275,276,3,104,52,0,276,277,5,17,
        0,0,277,278,5,18,0,0,278,279,5,6,0,0,279,281,3,18,9,0,280,282,3,
        16,8,0,281,280,1,0,0,0,281,282,1,0,0,0,282,283,1,0,0,0,283,284,5,
        11,0,0,284,286,1,0,0,0,285,256,1,0,0,0,285,265,1,0,0,0,285,274,1,
        0,0,0,286,15,1,0,0,0,287,288,5,19,0,0,288,289,3,104,52,0,289,17,
        1,0,0,0,290,294,3,30,15,0,291,294,3,20,10,0,292,294,3,22,11,0,293,
        290,1,0,0,0,293,291,1,0,0,0,293,292,1,0,0,0,294,19,1,0,0,0,295,296,
        5,121,0,0,296,298,5,2,0,0,297,299,3,24,12,0,298,297,1,0,0,0,298,
        299,1,0,0,0,299,300,1,0,0,0,300,301,5,3,0,0,301,21,1,0,0,0,302,303,
        5,20,0,0,303,304,5,2,0,0,304,305,3,20,10,0,305,306,5,3,0,0,306,23,
        1,0,0,0,307,312,3,26,13,0,308,309,5,6,0,0,309,311,3,26,13,0,310,
        308,1,0,0,0,311,314,1,0,0,0,312,310,1,0,0,0,312,313,1,0,0,0,313,
        25,1,0,0,0,314,312,1,0,0,0,315,316,5,121,0,0,316,318,5,21,0,0,317,
        315,1,0,0,0,317,318,1,0,0,0,318,319,1,0,0,0,319,320,3,28,14,0,320,
        27,1,0,0,0,321,326,3,86,43,0,322,326,3,118,59,0,323,326,3,102,51,
        0,324,326,3,164,82,0,325,321,1,0,0,0,325,322,1,0,0,0,325,323,1,0,
        0,0,325,324,1,0,0,0,326,29,1,0,0,0,327,338,3,34,17,0,328,338,3,36,
        18,0,329,338,3,38,19,0,330,338,3,40,20,0,331,338,3,42,21,0,332,338,
        3,44,22,0,333,338,3,46,23,0,334,338,3,48,24,0,335,338,3,50,25,0,
        336,338,3,32,16,0,337,327,1,0,0,0,337,328,1,0,0,0,337,329,1,0,0,
        0,337,330,1,0,0,0,337,331,1,0,0,0,337,332,1,0,0,0,337,333,1,0,0,
        0,337,334,1,0,0,0,337,335,1,0,0,0,337,336,1,0,0,0,338,31,1,0,0,0,
        339,340,5,22,0,0,340,341,5,120,0,0,341,33,1,0,0,0,342,343,7,0,0,
        0,343,344,5,25,0,0,344,345,3,104,52,0,345,35,1,0,0,0,346,347,7,0,
        0,0,347,348,5,26,0,0,348,349,3,104,52,0,349,37,1,0,0,0,350,351,7,
        1,0,0,351,352,5,29,0,0,352,353,3,86,43,0,353,354,5,30,0,0,354,355,
        3,106,53,0,355,357,5,119,0,0,356,358,3,96,48,0,357,356,1,0,0,0,357,
        358,1,0,0,0,358,39,1,0,0,0,359,360,7,1,0,0,360,361,5,31,0,0,361,
        362,3,86,43,0,362,363,5,30,0,0,363,364,3,106,53,0,364,366,5,119,
        0,0,365,367,3,96,48,0,366,365,1,0,0,0,366,367,1,0,0,0,367,41,1,0,
        0,0,368,369,5,7,0,0,369,370,5,29,0,0,370,371,3,86,43,0,371,373,3,
        98,49,0,372,374,3,96,48,0,373,372,1,0,0,0,373,374,1,0,0,0,374,43,
        1,0,0,0,375,376,5,7,0,0,376,377,5,31,0,0,377,378,3,86,43,0,378,380,
        3,98,49,0,379,381,3,96,48,0,380,379,1,0,0,0,380,381,1,0,0,0,381,
        45,1,0,0,0,382,383,5,32,0,0,383,384,5,33,0,0,384,385,5,14,0,0,385,
        386,3,82,41,0,386,47,1,0,0,0,387,388,5,34,0,0,388,389,5,33,0,0,389,
        390,5,14,0,0,390,391,3,82,41,0,391,49,1,0,0,0,392,393,5,35,0,0,393,
        394,5,36,0,0,394,401,5,37,0,0,395,398,3,52,26,0,396,397,5,6,0,0,
        397,399,3,54,27,0,398,396,1,0,0,0,398,399,1,0,0,0,399,402,1,0,0,
        0,400,402,3,54,27,0,401,395,1,0,0,0,401,400,1,0,0,0,402,407,1,0,
        0,0,403,404,5,6,0,0,404,406,3,56,28,0,405,403,1,0,0,0,406,409,1,
        0,0,0,407,405,1,0,0,0,407,408,1,0,0,0,408,51,1,0,0,0,409,407,1,0,
        0,0,410,415,3,58,29,0,411,412,5,6,0,0,412,414,3,58,29,0,413,411,
        1,0,0,0,414,417,1,0,0,0,415,413,1,0,0,0,415,416,1,0,0,0,416,53,1,
        0,0,0,417,415,1,0,0,0,418,423,3,60,30,0,419,420,5,6,0,0,420,422,
        3,60,30,0,421,419,1,0,0,0,422,425,1,0,0,0,423,421,1,0,0,0,423,424,
        1,0,0,0,424,55,1,0,0,0,425,423,1,0,0,0,426,430,3,62,31,0,427,430,
        3,66,33,0,428,430,3,70,35,0,429,426,1,0,0,0,429,427,1,0,0,0,429,
        428,1,0,0,0,430,57,1,0,0,0,431,432,5,38,0,0,432,433,5,39,0,0,433,
        434,5,120,0,0,434,435,5,10,0,0,435,436,5,120,0,0,436,59,1,0,0,0,
        437,438,5,40,0,0,438,439,5,120,0,0,439,61,1,0,0,0,440,441,5,41,0,
        0,441,442,3,64,32,0,442,63,1,0,0,0,443,444,5,42,0,0,444,445,5,118,
        0,0,445,455,3,120,60,0,446,447,5,43,0,0,447,448,5,44,0,0,448,449,
        5,118,0,0,449,450,3,120,60,0,450,451,5,45,0,0,451,452,5,118,0,0,
        452,453,3,120,60,0,453,455,1,0,0,0,454,443,1,0,0,0,454,446,1,0,0,
        0,455,65,1,0,0,0,456,457,5,46,0,0,457,458,3,68,34,0,458,67,1,0,0,
        0,459,460,5,42,0,0,460,464,3,164,82,0,461,462,5,47,0,0,462,464,5,
        118,0,0,463,459,1,0,0,0,463,461,1,0,0,0,464,69,1,0,0,0,465,466,5,
        48,0,0,466,467,3,72,36,0,467,71,1,0,0,0,468,471,5,49,0,0,469,470,
        5,50,0,0,470,472,5,118,0,0,471,469,1,0,0,0,471,472,1,0,0,0,472,484,
        1,0,0,0,473,474,5,51,0,0,474,484,3,74,37,0,475,476,5,52,0,0,476,
        484,3,74,37,0,477,478,5,53,0,0,478,484,3,76,38,0,479,480,5,54,0,
        0,480,484,3,78,39,0,481,482,5,55,0,0,482,484,3,80,40,0,483,468,1,
        0,0,0,483,473,1,0,0,0,483,475,1,0,0,0,483,477,1,0,0,0,483,479,1,
        0,0,0,483,481,1,0,0,0,484,73,1,0,0,0,485,486,5,50,0,0,486,488,5,
        118,0,0,487,485,1,0,0,0,487,488,1,0,0,0,488,489,1,0,0,0,489,490,
        5,56,0,0,490,491,5,118,0,0,491,492,5,10,0,0,492,493,5,118,0,0,493,
        75,1,0,0,0,494,495,5,50,0,0,495,497,5,118,0,0,496,494,1,0,0,0,496,
        497,1,0,0,0,497,500,1,0,0,0,498,499,5,57,0,0,499,501,5,118,0,0,500,
        498,1,0,0,0,500,501,1,0,0,0,501,77,1,0,0,0,502,503,5,50,0,0,503,
        505,5,118,0,0,504,502,1,0,0,0,504,505,1,0,0,0,505,506,1,0,0,0,506,
        507,5,30,0,0,507,508,5,118,0,0,508,79,1,0,0,0,509,510,5,50,0,0,510,
        512,5,118,0,0,511,509,1,0,0,0,511,512,1,0,0,0,512,515,1,0,0,0,513,
        514,5,30,0,0,514,516,5,118,0,0,515,513,1,0,0,0,515,516,1,0,0,0,516,
        81,1,0,0,0,517,518,3,84,42,0,518,519,3,104,52,0,519,83,1,0,0,0,520,
        521,7,2,0,0,521,85,1,0,0,0,522,527,3,104,52,0,523,527,3,88,44,0,
        524,527,3,92,46,0,525,527,3,94,47,0,526,522,1,0,0,0,526,523,1,0,
        0,0,526,524,1,0,0,0,526,525,1,0,0,0,527,87,1,0,0,0,528,529,5,71,
        0,0,529,534,3,90,45,0,530,531,5,6,0,0,531,533,3,90,45,0,532,530,
        1,0,0,0,533,536,1,0,0,0,534,532,1,0,0,0,534,535,1,0,0,0,535,537,
        1,0,0,0,536,534,1,0,0,0,537,538,5,72,0,0,538,89,1,0,0,0,539,540,
        3,104,52,0,540,91,1,0,0,0,541,543,5,73,0,0,542,544,3,104,52,0,543,
        542,1,0,0,0,543,544,1,0,0,0,544,545,1,0,0,0,545,546,3,88,44,0,546,
        93,1,0,0,0,547,548,5,74,0,0,548,549,5,73,0,0,549,550,3,108,54,0,
        550,95,1,0,0,0,551,552,7,3,0,0,552,97,1,0,0,0,553,554,5,39,0,0,554,
        556,3,100,50,0,555,553,1,0,0,0,555,556,1,0,0,0,556,557,1,0,0,0,557,
        558,5,10,0,0,558,559,3,100,50,0,559,99,1,0,0,0,560,561,3,102,51,
        0,561,101,1,0,0,0,562,564,7,4,0,0,563,562,1,0,0,0,563,564,1,0,0,
        0,564,565,1,0,0,0,565,566,3,106,53,0,566,103,1,0,0,0,567,568,7,5,
        0,0,568,105,1,0,0,0,569,570,7,6,0,0,570,107,1,0,0,0,571,575,3,110,
        55,0,572,575,3,112,56,0,573,575,3,114,57,0,574,571,1,0,0,0,574,572,
        1,0,0,0,574,573,1,0,0,0,575,109,1,0,0,0,576,577,5,81,0,0,577,578,
        3,104,52,0,578,579,5,82,0,0,579,580,3,84,42,0,580,111,1,0,0,0,581,
        582,5,83,0,0,582,583,5,30,0,0,583,584,3,116,58,0,584,585,3,104,52,
        0,585,586,5,82,0,0,586,587,3,84,42,0,587,113,1,0,0,0,588,589,5,84,
        0,0,589,590,3,116,58,0,590,591,3,162,81,0,591,593,3,106,53,0,592,
        594,3,168,84,0,593,592,1,0,0,0,593,594,1,0,0,0,594,595,1,0,0,0,595,
        596,5,82,0,0,596,597,3,84,42,0,597,115,1,0,0,0,598,599,3,104,52,
        0,599,117,1,0,0,0,600,601,3,106,53,0,601,602,3,120,60,0,602,119,
        1,0,0,0,603,604,7,7,0,0,604,121,1,0,0,0,605,608,3,124,62,0,606,608,
        3,128,64,0,607,605,1,0,0,0,607,606,1,0,0,0,608,123,1,0,0,0,609,613,
        3,118,59,0,610,613,3,126,63,0,611,613,5,121,0,0,612,609,1,0,0,0,
        612,610,1,0,0,0,612,611,1,0,0,0,613,125,1,0,0,0,614,617,5,91,0,0,
        615,616,7,4,0,0,616,618,3,118,59,0,617,615,1,0,0,0,617,618,1,0,0,
        0,618,127,1,0,0,0,619,620,5,71,0,0,620,621,3,124,62,0,621,622,5,
        6,0,0,622,623,3,124,62,0,623,627,5,72,0,0,624,625,5,92,0,0,625,626,
        5,93,0,0,626,628,3,138,69,0,627,624,1,0,0,0,627,628,1,0,0,0,628,
        129,1,0,0,0,629,632,3,132,66,0,630,632,3,136,68,0,631,629,1,0,0,
        0,631,630,1,0,0,0,632,131,1,0,0,0,633,636,3,134,67,0,634,636,5,121,
        0,0,635,633,1,0,0,0,635,634,1,0,0,0,636,133,1,0,0,0,637,638,3,102,
        51,0,638,639,3,120,60,0,639,135,1,0,0,0,640,641,5,71,0,0,641,642,
        3,132,66,0,642,643,5,6,0,0,643,644,3,132,66,0,644,648,5,72,0,0,645,
        646,5,92,0,0,646,647,5,93,0,0,647,649,3,138,69,0,648,645,1,0,0,0,
        648,649,1,0,0,0,649,137,1,0,0,0,650,651,7,8,0,0,651,139,1,0,0,0,
        652,653,3,142,71,0,653,141,1,0,0,0,654,655,3,144,72,0,655,143,1,
        0,0,0,656,661,3,146,73,0,657,658,5,95,0,0,658,660,3,146,73,0,659,
        657,1,0,0,0,660,663,1,0,0,0,661,659,1,0,0,0,661,662,1,0,0,0,662,
        145,1,0,0,0,663,661,1,0,0,0,664,669,3,148,74,0,665,666,5,96,0,0,
        666,668,3,148,74,0,667,665,1,0,0,0,668,671,1,0,0,0,669,667,1,0,0,
        0,669,670,1,0,0,0,670,147,1,0,0,0,671,669,1,0,0,0,672,678,3,150,
        75,0,673,674,5,2,0,0,674,675,3,144,72,0,675,676,5,3,0,0,676,678,
        1,0,0,0,677,672,1,0,0,0,677,673,1,0,0,0,678,149,1,0,0,0,679,682,
        3,152,76,0,680,682,3,164,82,0,681,679,1,0,0,0,681,680,1,0,0,0,682,
        151,1,0,0,0,683,684,3,154,77,0,684,685,3,162,81,0,685,686,3,154,
        77,0,686,153,1,0,0,0,687,692,3,156,78,0,688,689,7,4,0,0,689,691,
        3,156,78,0,690,688,1,0,0,0,691,694,1,0,0,0,692,690,1,0,0,0,692,693,
        1,0,0,0,693,155,1,0,0,0,694,692,1,0,0,0,695,700,3,158,79,0,696,697,
        7,9,0,0,697,699,3,158,79,0,698,696,1,0,0,0,699,702,1,0,0,0,700,698,
        1,0,0,0,700,701,1,0,0,0,701,157,1,0,0,0,702,700,1,0,0,0,703,710,
        3,160,80,0,704,710,3,166,83,0,705,706,5,2,0,0,706,707,3,154,77,0,
        707,708,5,3,0,0,708,710,1,0,0,0,709,703,1,0,0,0,709,704,1,0,0,0,
        709,705,1,0,0,0,710,159,1,0,0,0,711,713,3,106,53,0,712,714,3,168,
        84,0,713,712,1,0,0,0,713,714,1,0,0,0,714,161,1,0,0,0,715,716,7,10,
        0,0,716,163,1,0,0,0,717,718,7,11,0,0,718,165,1,0,0,0,719,720,5,107,
        0,0,720,721,5,14,0,0,721,722,5,61,0,0,722,741,3,104,52,0,723,724,
        5,108,0,0,724,725,5,14,0,0,725,726,5,61,0,0,726,741,3,104,52,0,727,
        728,5,109,0,0,728,729,5,110,0,0,729,730,5,82,0,0,730,731,5,26,0,
        0,731,741,3,104,52,0,732,733,5,111,0,0,733,734,5,82,0,0,734,735,
        5,26,0,0,735,741,3,104,52,0,736,737,5,112,0,0,737,738,5,82,0,0,738,
        739,5,26,0,0,739,741,3,104,52,0,740,719,1,0,0,0,740,723,1,0,0,0,
        740,727,1,0,0,0,740,732,1,0,0,0,740,736,1,0,0,0,741,167,1,0,0,0,
        742,743,7,12,0,0,743,169,1,0,0,0,63,173,182,188,195,205,226,230,
        239,250,254,261,270,281,285,293,298,312,317,325,337,357,366,373,
        380,398,401,407,415,423,429,454,463,471,483,487,496,500,504,511,
        515,526,534,543,555,563,574,593,607,612,617,627,631,635,648,661,
        669,677,681,692,700,709,713,740
    ]

class PowerEventDSLParser ( Parser ):

    grammarFileName = "PowerEventDSL.g4"

    atn = ATNDeserializer().deserialize(serializedATN())

    decisionsToDFA = [ DFA(ds, i) for i, ds in enumerate(atn.decisionToState) ]

    sharedContextCache = PredictionContextCache()

    literalNames = [ "<INVALID>", "'func'", "'('", "')'", "'{'", "'}'", 
                     "','", "'set'", "'simulation'", "'duration'", "'to'", 
                     "';'", "'time'", "'step'", "'at'", "'when'", "'after'", 
                     "'is'", "'completed'", "'tagged'", "'checkAndApply'", 
                     "':'", "'print'", "'open'", "'close'", "'switch'", 
                     "'line'", "'increase'", "'decrease'", "'load'", "'by'", 
                     "'generator'", "'apply'", "'fault'", "'clear'", "'change'", 
                     "'network'", "'characteristics'", "'link'", "'from'", 
                     "'node'", "'delay'", "'fixed'", "'gauss'", "'mean'", 
                     "'stddev'", "'drop'", "'random'", "'corruption'", "'none'", 
                     "'likelihood'", "'random_noise_measurement'", "'random_noise_control'", 
                     "'zero_out_measurement'", "'shift_measurement'", "'invert_control'", 
                     "'range'", "'value'", "'twoWindingsTransformer'", "'threeWindingsTransformer'", 
                     "'substation'", "'voltageLevel'", "'busbarSection'", 
                     "'battery'", "'shunt'", "'staticVarCompensator'", "'hvdcLine'", 
                     "'bus'", "'asset'", "'2_windings_transformer'", "'3_windings_transformer'", 
                     "'['", "']'", "'cluster'", "'dynamic'", "'P'", "'Q'", 
                     "'U'", "'state'", "'+'", "'-'", "'regex'", "'on'", 
                     "'group'", "'where'", "'seconds'", "'second'", "'minutes'", 
                     "'minute'", "'hours'", "'hour'", "'now'", "'with'", 
                     "'law'", "'linear'", "'or'", "'and'", "'*'", "'/'", 
                     "'<'", "'>'", "'<='", "'>='", "'=='", "'!='", "'true'", 
                     "'false'", "'voltage'", "'frequency'", "'power'", "'flow'", 
                     "'active_flow'", "'reactive_flow'", "'pu'", "'Hz'", 
                     "'MW'", "'MVar'", "'kV'", "<INVALID>", "'%'" ]

    symbolicNames = [ "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                      "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                      "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                      "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                      "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                      "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                      "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                      "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                      "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                      "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                      "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                      "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                      "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                      "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                      "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                      "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                      "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                      "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                      "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                      "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                      "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                      "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                      "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                      "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                      "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                      "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                      "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                      "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                      "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                      "<INVALID>", "<INVALID>", "NUMBER", "PERCENT", "STRING", 
                      "IDENTIFIER", "WS", "COMMENT" ]

    RULE_program = 0
    RULE_statement = 1
    RULE_functionDef = 2
    RULE_functionParamList = 3
    RULE_setDuration = 4
    RULE_setTimeStep = 5
    RULE_eventDef = 6
    RULE_functionStatement = 7
    RULE_tagged = 8
    RULE_executable = 9
    RULE_callExpr = 10
    RULE_verifiedCallExpr = 11
    RULE_callArgList = 12
    RULE_callArg = 13
    RULE_callArgValue = 14
    RULE_action = 15
    RULE_printAction = 16
    RULE_switchAction = 17
    RULE_lineAction = 18
    RULE_loadAction = 19
    RULE_genAction = 20
    RULE_setLoadAction = 21
    RULE_setGenAction = 22
    RULE_faultAction = 23
    RULE_clearFaultAction = 24
    RULE_networkAction = 25
    RULE_linkStatement = 26
    RULE_nodeStatement = 27
    RULE_networkAdjustmentClause = 28
    RULE_linkClause = 29
    RULE_nodeClause = 30
    RULE_delayClause = 31
    RULE_delayFunction = 32
    RULE_dropClause = 33
    RULE_dropFunction = 34
    RULE_corruptionClause = 35
    RULE_corruptionFunction = 36
    RULE_corruptionNoiseParams = 37
    RULE_corruptionZeroParams = 38
    RULE_corruptionShiftParams = 39
    RULE_corruptionInvertParams = 40
    RULE_component = 41
    RULE_componentType = 42
    RULE_target = 43
    RULE_listSpec = 44
    RULE_listItem = 45
    RULE_clusterSpec = 46
    RULE_dynamicClusterSpec = 47
    RULE_channelSpec = 48
    RULE_setRange = 49
    RULE_signedNumber = 50
    RULE_signedNumericAtom = 51
    RULE_stringAtom = 52
    RULE_numericAtom = 53
    RULE_relationshipSpec = 54
    RULE_regexFilter = 55
    RULE_groupByFilter = 56
    RULE_propertyFilter = 57
    RULE_propertyName = 58
    RULE_timeValue = 59
    RULE_timeUnit = 60
    RULE_timeSpec = 61
    RULE_timeExpr = 62
    RULE_nowExpr = 63
    RULE_intervalSpec = 64
    RULE_relativeTimeSpec = 65
    RULE_relativeTimeExpr = 66
    RULE_relativeTimeValue = 67
    RULE_relativeIntervalSpec = 68
    RULE_lawSpec = 69
    RULE_dynamicExpression = 70
    RULE_expression = 71
    RULE_booleanExpr = 72
    RULE_booleanTerm = 73
    RULE_booleanFactor = 74
    RULE_booleanAtomic = 75
    RULE_comparisonExpr = 76
    RULE_arithmeticExpr = 77
    RULE_term = 78
    RULE_factor = 79
    RULE_numberWithUnit = 80
    RULE_comparison = 81
    RULE_booleanLiteral = 82
    RULE_variable = 83
    RULE_unit = 84

    ruleNames =  [ "program", "statement", "functionDef", "functionParamList", 
                   "setDuration", "setTimeStep", "eventDef", "functionStatement", 
                   "tagged", "executable", "callExpr", "verifiedCallExpr", 
                   "callArgList", "callArg", "callArgValue", "action", "printAction", 
                   "switchAction", "lineAction", "loadAction", "genAction", 
                   "setLoadAction", "setGenAction", "faultAction", "clearFaultAction", 
                   "networkAction", "linkStatement", "nodeStatement", "networkAdjustmentClause", 
                   "linkClause", "nodeClause", "delayClause", "delayFunction", 
                   "dropClause", "dropFunction", "corruptionClause", "corruptionFunction", 
                   "corruptionNoiseParams", "corruptionZeroParams", "corruptionShiftParams", 
                   "corruptionInvertParams", "component", "componentType", 
                   "target", "listSpec", "listItem", "clusterSpec", "dynamicClusterSpec", 
                   "channelSpec", "setRange", "signedNumber", "signedNumericAtom", 
                   "stringAtom", "numericAtom", "relationshipSpec", "regexFilter", 
                   "groupByFilter", "propertyFilter", "propertyName", "timeValue", 
                   "timeUnit", "timeSpec", "timeExpr", "nowExpr", "intervalSpec", 
                   "relativeTimeSpec", "relativeTimeExpr", "relativeTimeValue", 
                   "relativeIntervalSpec", "lawSpec", "dynamicExpression", 
                   "expression", "booleanExpr", "booleanTerm", "booleanFactor", 
                   "booleanAtomic", "comparisonExpr", "arithmeticExpr", 
                   "term", "factor", "numberWithUnit", "comparison", "booleanLiteral", 
                   "variable", "unit" ]

    EOF = Token.EOF
    T__0=1
    T__1=2
    T__2=3
    T__3=4
    T__4=5
    T__5=6
    T__6=7
    T__7=8
    T__8=9
    T__9=10
    T__10=11
    T__11=12
    T__12=13
    T__13=14
    T__14=15
    T__15=16
    T__16=17
    T__17=18
    T__18=19
    T__19=20
    T__20=21
    T__21=22
    T__22=23
    T__23=24
    T__24=25
    T__25=26
    T__26=27
    T__27=28
    T__28=29
    T__29=30
    T__30=31
    T__31=32
    T__32=33
    T__33=34
    T__34=35
    T__35=36
    T__36=37
    T__37=38
    T__38=39
    T__39=40
    T__40=41
    T__41=42
    T__42=43
    T__43=44
    T__44=45
    T__45=46
    T__46=47
    T__47=48
    T__48=49
    T__49=50
    T__50=51
    T__51=52
    T__52=53
    T__53=54
    T__54=55
    T__55=56
    T__56=57
    T__57=58
    T__58=59
    T__59=60
    T__60=61
    T__61=62
    T__62=63
    T__63=64
    T__64=65
    T__65=66
    T__66=67
    T__67=68
    T__68=69
    T__69=70
    T__70=71
    T__71=72
    T__72=73
    T__73=74
    T__74=75
    T__75=76
    T__76=77
    T__77=78
    T__78=79
    T__79=80
    T__80=81
    T__81=82
    T__82=83
    T__83=84
    T__84=85
    T__85=86
    T__86=87
    T__87=88
    T__88=89
    T__89=90
    T__90=91
    T__91=92
    T__92=93
    T__93=94
    T__94=95
    T__95=96
    T__96=97
    T__97=98
    T__98=99
    T__99=100
    T__100=101
    T__101=102
    T__102=103
    T__103=104
    T__104=105
    T__105=106
    T__106=107
    T__107=108
    T__108=109
    T__109=110
    T__110=111
    T__111=112
    T__112=113
    T__113=114
    T__114=115
    T__115=116
    T__116=117
    NUMBER=118
    PERCENT=119
    STRING=120
    IDENTIFIER=121
    WS=122
    COMMENT=123

    def __init__(self, input:TokenStream, output:TextIO = sys.stdout):
        super().__init__(input, output)
        self.checkVersion("4.13.2")
        self._interp = ParserATNSimulator(self, self.atn, self.decisionsToDFA, self.sharedContextCache)
        self._predicates = None




    class ProgramContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def EOF(self):
            return self.getToken(PowerEventDSLParser.EOF, 0)

        def statement(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(PowerEventDSLParser.StatementContext)
            else:
                return self.getTypedRuleContext(PowerEventDSLParser.StatementContext,i)


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_program

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterProgram" ):
                listener.enterProgram(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitProgram" ):
                listener.exitProgram(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitProgram" ):
                return visitor.visitProgram(self)
            else:
                return visitor.visitChildren(self)




    def program(self):

        localctx = PowerEventDSLParser.ProgramContext(self, self._ctx, self.state)
        self.enterRule(localctx, 0, self.RULE_program)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 173
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while (((_la) & ~0x3f) == 0 and ((1 << _la) & 56267751554) != 0) or _la==121:
                self.state = 170
                self.statement()
                self.state = 175
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 176
            self.match(PowerEventDSLParser.EOF)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class StatementContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def setDuration(self):
            return self.getTypedRuleContext(PowerEventDSLParser.SetDurationContext,0)


        def setTimeStep(self):
            return self.getTypedRuleContext(PowerEventDSLParser.SetTimeStepContext,0)


        def functionDef(self):
            return self.getTypedRuleContext(PowerEventDSLParser.FunctionDefContext,0)


        def eventDef(self):
            return self.getTypedRuleContext(PowerEventDSLParser.EventDefContext,0)


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_statement

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterStatement" ):
                listener.enterStatement(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitStatement" ):
                listener.exitStatement(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitStatement" ):
                return visitor.visitStatement(self)
            else:
                return visitor.visitChildren(self)




    def statement(self):

        localctx = PowerEventDSLParser.StatementContext(self, self._ctx, self.state)
        self.enterRule(localctx, 2, self.RULE_statement)
        try:
            self.state = 182
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,1,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 178
                self.setDuration()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 179
                self.setTimeStep()
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 180
                self.functionDef()
                pass

            elif la_ == 4:
                self.enterOuterAlt(localctx, 4)
                self.state = 181
                self.eventDef()
                pass


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class FunctionDefContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def IDENTIFIER(self):
            return self.getToken(PowerEventDSLParser.IDENTIFIER, 0)

        def functionParamList(self):
            return self.getTypedRuleContext(PowerEventDSLParser.FunctionParamListContext,0)


        def functionStatement(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(PowerEventDSLParser.FunctionStatementContext)
            else:
                return self.getTypedRuleContext(PowerEventDSLParser.FunctionStatementContext,i)


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_functionDef

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterFunctionDef" ):
                listener.enterFunctionDef(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitFunctionDef" ):
                listener.exitFunctionDef(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitFunctionDef" ):
                return visitor.visitFunctionDef(self)
            else:
                return visitor.visitChildren(self)




    def functionDef(self):

        localctx = PowerEventDSLParser.FunctionDefContext(self, self._ctx, self.state)
        self.enterRule(localctx, 4, self.RULE_functionDef)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 184
            self.match(PowerEventDSLParser.T__0)
            self.state = 185
            self.match(PowerEventDSLParser.IDENTIFIER)
            self.state = 186
            self.match(PowerEventDSLParser.T__1)
            self.state = 188
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==121:
                self.state = 187
                self.functionParamList()


            self.state = 190
            self.match(PowerEventDSLParser.T__2)
            self.state = 191
            self.match(PowerEventDSLParser.T__3)
            self.state = 195
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while (((_la) & ~0x3f) == 0 and ((1 << _la) & 114688) != 0):
                self.state = 192
                self.functionStatement()
                self.state = 197
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 198
            self.match(PowerEventDSLParser.T__4)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class FunctionParamListContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def IDENTIFIER(self, i:int=None):
            if i is None:
                return self.getTokens(PowerEventDSLParser.IDENTIFIER)
            else:
                return self.getToken(PowerEventDSLParser.IDENTIFIER, i)

        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_functionParamList

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterFunctionParamList" ):
                listener.enterFunctionParamList(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitFunctionParamList" ):
                listener.exitFunctionParamList(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitFunctionParamList" ):
                return visitor.visitFunctionParamList(self)
            else:
                return visitor.visitChildren(self)




    def functionParamList(self):

        localctx = PowerEventDSLParser.FunctionParamListContext(self, self._ctx, self.state)
        self.enterRule(localctx, 6, self.RULE_functionParamList)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 200
            self.match(PowerEventDSLParser.IDENTIFIER)
            self.state = 205
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==6:
                self.state = 201
                self.match(PowerEventDSLParser.T__5)
                self.state = 202
                self.match(PowerEventDSLParser.IDENTIFIER)
                self.state = 207
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class SetDurationContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def timeValue(self):
            return self.getTypedRuleContext(PowerEventDSLParser.TimeValueContext,0)


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_setDuration

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterSetDuration" ):
                listener.enterSetDuration(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitSetDuration" ):
                listener.exitSetDuration(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSetDuration" ):
                return visitor.visitSetDuration(self)
            else:
                return visitor.visitChildren(self)




    def setDuration(self):

        localctx = PowerEventDSLParser.SetDurationContext(self, self._ctx, self.state)
        self.enterRule(localctx, 8, self.RULE_setDuration)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 208
            self.match(PowerEventDSLParser.T__6)
            self.state = 209
            self.match(PowerEventDSLParser.T__7)
            self.state = 210
            self.match(PowerEventDSLParser.T__8)
            self.state = 211
            self.match(PowerEventDSLParser.T__9)
            self.state = 212
            self.timeValue()
            self.state = 213
            self.match(PowerEventDSLParser.T__10)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class SetTimeStepContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def timeValue(self):
            return self.getTypedRuleContext(PowerEventDSLParser.TimeValueContext,0)


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_setTimeStep

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterSetTimeStep" ):
                listener.enterSetTimeStep(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitSetTimeStep" ):
                listener.exitSetTimeStep(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSetTimeStep" ):
                return visitor.visitSetTimeStep(self)
            else:
                return visitor.visitChildren(self)




    def setTimeStep(self):

        localctx = PowerEventDSLParser.SetTimeStepContext(self, self._ctx, self.state)
        self.enterRule(localctx, 10, self.RULE_setTimeStep)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 215
            self.match(PowerEventDSLParser.T__6)
            self.state = 216
            self.match(PowerEventDSLParser.T__11)
            self.state = 217
            self.match(PowerEventDSLParser.T__12)
            self.state = 218
            self.match(PowerEventDSLParser.T__9)
            self.state = 219
            self.timeValue()
            self.state = 220
            self.match(PowerEventDSLParser.T__10)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class EventDefContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def executable(self):
            return self.getTypedRuleContext(PowerEventDSLParser.ExecutableContext,0)


        def timeSpec(self):
            return self.getTypedRuleContext(PowerEventDSLParser.TimeSpecContext,0)


        def tagged(self):
            return self.getTypedRuleContext(PowerEventDSLParser.TaggedContext,0)


        def dynamicExpression(self):
            return self.getTypedRuleContext(PowerEventDSLParser.DynamicExpressionContext,0)


        def stringAtom(self):
            return self.getTypedRuleContext(PowerEventDSLParser.StringAtomContext,0)


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_eventDef

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterEventDef" ):
                listener.enterEventDef(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitEventDef" ):
                listener.exitEventDef(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitEventDef" ):
                return visitor.visitEventDef(self)
            else:
                return visitor.visitChildren(self)




    def eventDef(self):

        localctx = PowerEventDSLParser.EventDefContext(self, self._ctx, self.state)
        self.enterRule(localctx, 12, self.RULE_eventDef)
        self._la = 0 # Token type
        try:
            self.state = 254
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [7, 14, 20, 22, 23, 24, 27, 28, 32, 34, 35, 121]:
                self.enterOuterAlt(localctx, 1)
                self.state = 226
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==14:
                    self.state = 222
                    self.match(PowerEventDSLParser.T__13)
                    self.state = 223
                    self.timeSpec()
                    self.state = 224
                    self.match(PowerEventDSLParser.T__5)


                self.state = 228
                self.executable()
                self.state = 230
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==19:
                    self.state = 229
                    self.tagged()


                self.state = 232
                self.match(PowerEventDSLParser.T__10)
                pass
            elif token in [15]:
                self.enterOuterAlt(localctx, 2)
                self.state = 234
                self.match(PowerEventDSLParser.T__14)
                self.state = 235
                self.dynamicExpression()
                self.state = 236
                self.match(PowerEventDSLParser.T__5)
                self.state = 237
                self.executable()
                self.state = 239
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==19:
                    self.state = 238
                    self.tagged()


                self.state = 241
                self.match(PowerEventDSLParser.T__10)
                pass
            elif token in [16]:
                self.enterOuterAlt(localctx, 3)
                self.state = 243
                self.match(PowerEventDSLParser.T__15)
                self.state = 244
                self.stringAtom()
                self.state = 245
                self.match(PowerEventDSLParser.T__16)
                self.state = 246
                self.match(PowerEventDSLParser.T__17)
                self.state = 247
                self.match(PowerEventDSLParser.T__5)
                self.state = 248
                self.executable()
                self.state = 250
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==19:
                    self.state = 249
                    self.tagged()


                self.state = 252
                self.match(PowerEventDSLParser.T__10)
                pass
            else:
                raise NoViableAltException(self)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class FunctionStatementContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def relativeTimeSpec(self):
            return self.getTypedRuleContext(PowerEventDSLParser.RelativeTimeSpecContext,0)


        def executable(self):
            return self.getTypedRuleContext(PowerEventDSLParser.ExecutableContext,0)


        def tagged(self):
            return self.getTypedRuleContext(PowerEventDSLParser.TaggedContext,0)


        def dynamicExpression(self):
            return self.getTypedRuleContext(PowerEventDSLParser.DynamicExpressionContext,0)


        def stringAtom(self):
            return self.getTypedRuleContext(PowerEventDSLParser.StringAtomContext,0)


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_functionStatement

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterFunctionStatement" ):
                listener.enterFunctionStatement(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitFunctionStatement" ):
                listener.exitFunctionStatement(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitFunctionStatement" ):
                return visitor.visitFunctionStatement(self)
            else:
                return visitor.visitChildren(self)




    def functionStatement(self):

        localctx = PowerEventDSLParser.FunctionStatementContext(self, self._ctx, self.state)
        self.enterRule(localctx, 14, self.RULE_functionStatement)
        self._la = 0 # Token type
        try:
            self.state = 285
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [14]:
                self.enterOuterAlt(localctx, 1)
                self.state = 256
                self.match(PowerEventDSLParser.T__13)
                self.state = 257
                self.relativeTimeSpec()
                self.state = 258
                self.match(PowerEventDSLParser.T__5)
                self.state = 259
                self.executable()
                self.state = 261
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==19:
                    self.state = 260
                    self.tagged()


                self.state = 263
                self.match(PowerEventDSLParser.T__10)
                pass
            elif token in [15]:
                self.enterOuterAlt(localctx, 2)
                self.state = 265
                self.match(PowerEventDSLParser.T__14)
                self.state = 266
                self.dynamicExpression()
                self.state = 267
                self.match(PowerEventDSLParser.T__5)
                self.state = 268
                self.executable()
                self.state = 270
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==19:
                    self.state = 269
                    self.tagged()


                self.state = 272
                self.match(PowerEventDSLParser.T__10)
                pass
            elif token in [16]:
                self.enterOuterAlt(localctx, 3)
                self.state = 274
                self.match(PowerEventDSLParser.T__15)
                self.state = 275
                self.stringAtom()
                self.state = 276
                self.match(PowerEventDSLParser.T__16)
                self.state = 277
                self.match(PowerEventDSLParser.T__17)
                self.state = 278
                self.match(PowerEventDSLParser.T__5)
                self.state = 279
                self.executable()
                self.state = 281
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==19:
                    self.state = 280
                    self.tagged()


                self.state = 283
                self.match(PowerEventDSLParser.T__10)
                pass
            else:
                raise NoViableAltException(self)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class TaggedContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def stringAtom(self):
            return self.getTypedRuleContext(PowerEventDSLParser.StringAtomContext,0)


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_tagged

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterTagged" ):
                listener.enterTagged(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitTagged" ):
                listener.exitTagged(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitTagged" ):
                return visitor.visitTagged(self)
            else:
                return visitor.visitChildren(self)




    def tagged(self):

        localctx = PowerEventDSLParser.TaggedContext(self, self._ctx, self.state)
        self.enterRule(localctx, 16, self.RULE_tagged)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 287
            self.match(PowerEventDSLParser.T__18)
            self.state = 288
            self.stringAtom()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ExecutableContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def action(self):
            return self.getTypedRuleContext(PowerEventDSLParser.ActionContext,0)


        def callExpr(self):
            return self.getTypedRuleContext(PowerEventDSLParser.CallExprContext,0)


        def verifiedCallExpr(self):
            return self.getTypedRuleContext(PowerEventDSLParser.VerifiedCallExprContext,0)


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_executable

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterExecutable" ):
                listener.enterExecutable(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitExecutable" ):
                listener.exitExecutable(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitExecutable" ):
                return visitor.visitExecutable(self)
            else:
                return visitor.visitChildren(self)




    def executable(self):

        localctx = PowerEventDSLParser.ExecutableContext(self, self._ctx, self.state)
        self.enterRule(localctx, 18, self.RULE_executable)
        try:
            self.state = 293
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [7, 22, 23, 24, 27, 28, 32, 34, 35]:
                self.enterOuterAlt(localctx, 1)
                self.state = 290
                self.action()
                pass
            elif token in [121]:
                self.enterOuterAlt(localctx, 2)
                self.state = 291
                self.callExpr()
                pass
            elif token in [20]:
                self.enterOuterAlt(localctx, 3)
                self.state = 292
                self.verifiedCallExpr()
                pass
            else:
                raise NoViableAltException(self)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class CallExprContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def IDENTIFIER(self):
            return self.getToken(PowerEventDSLParser.IDENTIFIER, 0)

        def callArgList(self):
            return self.getTypedRuleContext(PowerEventDSLParser.CallArgListContext,0)


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_callExpr

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterCallExpr" ):
                listener.enterCallExpr(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitCallExpr" ):
                listener.exitCallExpr(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitCallExpr" ):
                return visitor.visitCallExpr(self)
            else:
                return visitor.visitChildren(self)




    def callExpr(self):

        localctx = PowerEventDSLParser.CallExprContext(self, self._ctx, self.state)
        self.enterRule(localctx, 20, self.RULE_callExpr)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 295
            self.match(PowerEventDSLParser.IDENTIFIER)
            self.state = 296
            self.match(PowerEventDSLParser.T__1)
            self.state = 298
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if ((((_la - 71)) & ~0x3f) == 0 and ((1 << (_la - 71)) & 1829638888227597) != 0):
                self.state = 297
                self.callArgList()


            self.state = 300
            self.match(PowerEventDSLParser.T__2)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class VerifiedCallExprContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def callExpr(self):
            return self.getTypedRuleContext(PowerEventDSLParser.CallExprContext,0)


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_verifiedCallExpr

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterVerifiedCallExpr" ):
                listener.enterVerifiedCallExpr(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitVerifiedCallExpr" ):
                listener.exitVerifiedCallExpr(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitVerifiedCallExpr" ):
                return visitor.visitVerifiedCallExpr(self)
            else:
                return visitor.visitChildren(self)




    def verifiedCallExpr(self):

        localctx = PowerEventDSLParser.VerifiedCallExprContext(self, self._ctx, self.state)
        self.enterRule(localctx, 22, self.RULE_verifiedCallExpr)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 302
            self.match(PowerEventDSLParser.T__19)
            self.state = 303
            self.match(PowerEventDSLParser.T__1)
            self.state = 304
            self.callExpr()
            self.state = 305
            self.match(PowerEventDSLParser.T__2)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class CallArgListContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def callArg(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(PowerEventDSLParser.CallArgContext)
            else:
                return self.getTypedRuleContext(PowerEventDSLParser.CallArgContext,i)


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_callArgList

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterCallArgList" ):
                listener.enterCallArgList(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitCallArgList" ):
                listener.exitCallArgList(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitCallArgList" ):
                return visitor.visitCallArgList(self)
            else:
                return visitor.visitChildren(self)




    def callArgList(self):

        localctx = PowerEventDSLParser.CallArgListContext(self, self._ctx, self.state)
        self.enterRule(localctx, 24, self.RULE_callArgList)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 307
            self.callArg()
            self.state = 312
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==6:
                self.state = 308
                self.match(PowerEventDSLParser.T__5)
                self.state = 309
                self.callArg()
                self.state = 314
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class CallArgContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def callArgValue(self):
            return self.getTypedRuleContext(PowerEventDSLParser.CallArgValueContext,0)


        def IDENTIFIER(self):
            return self.getToken(PowerEventDSLParser.IDENTIFIER, 0)

        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_callArg

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterCallArg" ):
                listener.enterCallArg(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitCallArg" ):
                listener.exitCallArg(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitCallArg" ):
                return visitor.visitCallArg(self)
            else:
                return visitor.visitChildren(self)




    def callArg(self):

        localctx = PowerEventDSLParser.CallArgContext(self, self._ctx, self.state)
        self.enterRule(localctx, 26, self.RULE_callArg)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 317
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,17,self._ctx)
            if la_ == 1:
                self.state = 315
                self.match(PowerEventDSLParser.IDENTIFIER)
                self.state = 316
                self.match(PowerEventDSLParser.T__20)


            self.state = 319
            self.callArgValue()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class CallArgValueContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def target(self):
            return self.getTypedRuleContext(PowerEventDSLParser.TargetContext,0)


        def timeValue(self):
            return self.getTypedRuleContext(PowerEventDSLParser.TimeValueContext,0)


        def signedNumericAtom(self):
            return self.getTypedRuleContext(PowerEventDSLParser.SignedNumericAtomContext,0)


        def booleanLiteral(self):
            return self.getTypedRuleContext(PowerEventDSLParser.BooleanLiteralContext,0)


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_callArgValue

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterCallArgValue" ):
                listener.enterCallArgValue(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitCallArgValue" ):
                listener.exitCallArgValue(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitCallArgValue" ):
                return visitor.visitCallArgValue(self)
            else:
                return visitor.visitChildren(self)




    def callArgValue(self):

        localctx = PowerEventDSLParser.CallArgValueContext(self, self._ctx, self.state)
        self.enterRule(localctx, 28, self.RULE_callArgValue)
        try:
            self.state = 325
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,18,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 321
                self.target()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 322
                self.timeValue()
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 323
                self.signedNumericAtom()
                pass

            elif la_ == 4:
                self.enterOuterAlt(localctx, 4)
                self.state = 324
                self.booleanLiteral()
                pass


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ActionContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def switchAction(self):
            return self.getTypedRuleContext(PowerEventDSLParser.SwitchActionContext,0)


        def lineAction(self):
            return self.getTypedRuleContext(PowerEventDSLParser.LineActionContext,0)


        def loadAction(self):
            return self.getTypedRuleContext(PowerEventDSLParser.LoadActionContext,0)


        def genAction(self):
            return self.getTypedRuleContext(PowerEventDSLParser.GenActionContext,0)


        def setLoadAction(self):
            return self.getTypedRuleContext(PowerEventDSLParser.SetLoadActionContext,0)


        def setGenAction(self):
            return self.getTypedRuleContext(PowerEventDSLParser.SetGenActionContext,0)


        def faultAction(self):
            return self.getTypedRuleContext(PowerEventDSLParser.FaultActionContext,0)


        def clearFaultAction(self):
            return self.getTypedRuleContext(PowerEventDSLParser.ClearFaultActionContext,0)


        def networkAction(self):
            return self.getTypedRuleContext(PowerEventDSLParser.NetworkActionContext,0)


        def printAction(self):
            return self.getTypedRuleContext(PowerEventDSLParser.PrintActionContext,0)


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_action

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterAction" ):
                listener.enterAction(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitAction" ):
                listener.exitAction(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitAction" ):
                return visitor.visitAction(self)
            else:
                return visitor.visitChildren(self)




    def action(self):

        localctx = PowerEventDSLParser.ActionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 30, self.RULE_action)
        try:
            self.state = 337
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,19,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 327
                self.switchAction()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 328
                self.lineAction()
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 329
                self.loadAction()
                pass

            elif la_ == 4:
                self.enterOuterAlt(localctx, 4)
                self.state = 330
                self.genAction()
                pass

            elif la_ == 5:
                self.enterOuterAlt(localctx, 5)
                self.state = 331
                self.setLoadAction()
                pass

            elif la_ == 6:
                self.enterOuterAlt(localctx, 6)
                self.state = 332
                self.setGenAction()
                pass

            elif la_ == 7:
                self.enterOuterAlt(localctx, 7)
                self.state = 333
                self.faultAction()
                pass

            elif la_ == 8:
                self.enterOuterAlt(localctx, 8)
                self.state = 334
                self.clearFaultAction()
                pass

            elif la_ == 9:
                self.enterOuterAlt(localctx, 9)
                self.state = 335
                self.networkAction()
                pass

            elif la_ == 10:
                self.enterOuterAlt(localctx, 10)
                self.state = 336
                self.printAction()
                pass


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class PrintActionContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def STRING(self):
            return self.getToken(PowerEventDSLParser.STRING, 0)

        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_printAction

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterPrintAction" ):
                listener.enterPrintAction(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitPrintAction" ):
                listener.exitPrintAction(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitPrintAction" ):
                return visitor.visitPrintAction(self)
            else:
                return visitor.visitChildren(self)




    def printAction(self):

        localctx = PowerEventDSLParser.PrintActionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 32, self.RULE_printAction)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 339
            self.match(PowerEventDSLParser.T__21)
            self.state = 340
            self.match(PowerEventDSLParser.STRING)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class SwitchActionContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def stringAtom(self):
            return self.getTypedRuleContext(PowerEventDSLParser.StringAtomContext,0)


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_switchAction

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterSwitchAction" ):
                listener.enterSwitchAction(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitSwitchAction" ):
                listener.exitSwitchAction(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSwitchAction" ):
                return visitor.visitSwitchAction(self)
            else:
                return visitor.visitChildren(self)




    def switchAction(self):

        localctx = PowerEventDSLParser.SwitchActionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 34, self.RULE_switchAction)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 342
            _la = self._input.LA(1)
            if not(_la==23 or _la==24):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
            self.state = 343
            self.match(PowerEventDSLParser.T__24)
            self.state = 344
            self.stringAtom()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class LineActionContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def stringAtom(self):
            return self.getTypedRuleContext(PowerEventDSLParser.StringAtomContext,0)


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_lineAction

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterLineAction" ):
                listener.enterLineAction(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitLineAction" ):
                listener.exitLineAction(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitLineAction" ):
                return visitor.visitLineAction(self)
            else:
                return visitor.visitChildren(self)




    def lineAction(self):

        localctx = PowerEventDSLParser.LineActionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 36, self.RULE_lineAction)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 346
            _la = self._input.LA(1)
            if not(_la==23 or _la==24):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
            self.state = 347
            self.match(PowerEventDSLParser.T__25)
            self.state = 348
            self.stringAtom()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class LoadActionContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def target(self):
            return self.getTypedRuleContext(PowerEventDSLParser.TargetContext,0)


        def numericAtom(self):
            return self.getTypedRuleContext(PowerEventDSLParser.NumericAtomContext,0)


        def PERCENT(self):
            return self.getToken(PowerEventDSLParser.PERCENT, 0)

        def channelSpec(self):
            return self.getTypedRuleContext(PowerEventDSLParser.ChannelSpecContext,0)


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_loadAction

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterLoadAction" ):
                listener.enterLoadAction(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitLoadAction" ):
                listener.exitLoadAction(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitLoadAction" ):
                return visitor.visitLoadAction(self)
            else:
                return visitor.visitChildren(self)




    def loadAction(self):

        localctx = PowerEventDSLParser.LoadActionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 38, self.RULE_loadAction)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 350
            _la = self._input.LA(1)
            if not(_la==27 or _la==28):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
            self.state = 351
            self.match(PowerEventDSLParser.T__28)
            self.state = 352
            self.target()
            self.state = 353
            self.match(PowerEventDSLParser.T__29)
            self.state = 354
            self.numericAtom()
            self.state = 355
            self.match(PowerEventDSLParser.PERCENT)
            self.state = 357
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if ((((_la - 75)) & ~0x3f) == 0 and ((1 << (_la - 75)) & 15) != 0):
                self.state = 356
                self.channelSpec()


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class GenActionContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def target(self):
            return self.getTypedRuleContext(PowerEventDSLParser.TargetContext,0)


        def numericAtom(self):
            return self.getTypedRuleContext(PowerEventDSLParser.NumericAtomContext,0)


        def PERCENT(self):
            return self.getToken(PowerEventDSLParser.PERCENT, 0)

        def channelSpec(self):
            return self.getTypedRuleContext(PowerEventDSLParser.ChannelSpecContext,0)


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_genAction

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterGenAction" ):
                listener.enterGenAction(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitGenAction" ):
                listener.exitGenAction(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitGenAction" ):
                return visitor.visitGenAction(self)
            else:
                return visitor.visitChildren(self)




    def genAction(self):

        localctx = PowerEventDSLParser.GenActionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 40, self.RULE_genAction)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 359
            _la = self._input.LA(1)
            if not(_la==27 or _la==28):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
            self.state = 360
            self.match(PowerEventDSLParser.T__30)
            self.state = 361
            self.target()
            self.state = 362
            self.match(PowerEventDSLParser.T__29)
            self.state = 363
            self.numericAtom()
            self.state = 364
            self.match(PowerEventDSLParser.PERCENT)
            self.state = 366
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if ((((_la - 75)) & ~0x3f) == 0 and ((1 << (_la - 75)) & 15) != 0):
                self.state = 365
                self.channelSpec()


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class SetLoadActionContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def target(self):
            return self.getTypedRuleContext(PowerEventDSLParser.TargetContext,0)


        def setRange(self):
            return self.getTypedRuleContext(PowerEventDSLParser.SetRangeContext,0)


        def channelSpec(self):
            return self.getTypedRuleContext(PowerEventDSLParser.ChannelSpecContext,0)


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_setLoadAction

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterSetLoadAction" ):
                listener.enterSetLoadAction(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitSetLoadAction" ):
                listener.exitSetLoadAction(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSetLoadAction" ):
                return visitor.visitSetLoadAction(self)
            else:
                return visitor.visitChildren(self)




    def setLoadAction(self):

        localctx = PowerEventDSLParser.SetLoadActionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 42, self.RULE_setLoadAction)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 368
            self.match(PowerEventDSLParser.T__6)
            self.state = 369
            self.match(PowerEventDSLParser.T__28)
            self.state = 370
            self.target()
            self.state = 371
            self.setRange()
            self.state = 373
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if ((((_la - 75)) & ~0x3f) == 0 and ((1 << (_la - 75)) & 15) != 0):
                self.state = 372
                self.channelSpec()


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class SetGenActionContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def target(self):
            return self.getTypedRuleContext(PowerEventDSLParser.TargetContext,0)


        def setRange(self):
            return self.getTypedRuleContext(PowerEventDSLParser.SetRangeContext,0)


        def channelSpec(self):
            return self.getTypedRuleContext(PowerEventDSLParser.ChannelSpecContext,0)


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_setGenAction

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterSetGenAction" ):
                listener.enterSetGenAction(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitSetGenAction" ):
                listener.exitSetGenAction(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSetGenAction" ):
                return visitor.visitSetGenAction(self)
            else:
                return visitor.visitChildren(self)




    def setGenAction(self):

        localctx = PowerEventDSLParser.SetGenActionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 44, self.RULE_setGenAction)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 375
            self.match(PowerEventDSLParser.T__6)
            self.state = 376
            self.match(PowerEventDSLParser.T__30)
            self.state = 377
            self.target()
            self.state = 378
            self.setRange()
            self.state = 380
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if ((((_la - 75)) & ~0x3f) == 0 and ((1 << (_la - 75)) & 15) != 0):
                self.state = 379
                self.channelSpec()


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class FaultActionContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def component(self):
            return self.getTypedRuleContext(PowerEventDSLParser.ComponentContext,0)


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_faultAction

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterFaultAction" ):
                listener.enterFaultAction(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitFaultAction" ):
                listener.exitFaultAction(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitFaultAction" ):
                return visitor.visitFaultAction(self)
            else:
                return visitor.visitChildren(self)




    def faultAction(self):

        localctx = PowerEventDSLParser.FaultActionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 46, self.RULE_faultAction)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 382
            self.match(PowerEventDSLParser.T__31)
            self.state = 383
            self.match(PowerEventDSLParser.T__32)
            self.state = 384
            self.match(PowerEventDSLParser.T__13)
            self.state = 385
            self.component()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ClearFaultActionContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def component(self):
            return self.getTypedRuleContext(PowerEventDSLParser.ComponentContext,0)


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_clearFaultAction

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterClearFaultAction" ):
                listener.enterClearFaultAction(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitClearFaultAction" ):
                listener.exitClearFaultAction(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitClearFaultAction" ):
                return visitor.visitClearFaultAction(self)
            else:
                return visitor.visitChildren(self)




    def clearFaultAction(self):

        localctx = PowerEventDSLParser.ClearFaultActionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 48, self.RULE_clearFaultAction)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 387
            self.match(PowerEventDSLParser.T__33)
            self.state = 388
            self.match(PowerEventDSLParser.T__32)
            self.state = 389
            self.match(PowerEventDSLParser.T__13)
            self.state = 390
            self.component()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class NetworkActionContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def linkStatement(self):
            return self.getTypedRuleContext(PowerEventDSLParser.LinkStatementContext,0)


        def nodeStatement(self):
            return self.getTypedRuleContext(PowerEventDSLParser.NodeStatementContext,0)


        def networkAdjustmentClause(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(PowerEventDSLParser.NetworkAdjustmentClauseContext)
            else:
                return self.getTypedRuleContext(PowerEventDSLParser.NetworkAdjustmentClauseContext,i)


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_networkAction

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterNetworkAction" ):
                listener.enterNetworkAction(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitNetworkAction" ):
                listener.exitNetworkAction(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitNetworkAction" ):
                return visitor.visitNetworkAction(self)
            else:
                return visitor.visitChildren(self)




    def networkAction(self):

        localctx = PowerEventDSLParser.NetworkActionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 50, self.RULE_networkAction)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 392
            self.match(PowerEventDSLParser.T__34)
            self.state = 393
            self.match(PowerEventDSLParser.T__35)
            self.state = 394
            self.match(PowerEventDSLParser.T__36)
            self.state = 401
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [38]:
                self.state = 395
                self.linkStatement()
                self.state = 398
                self._errHandler.sync(self)
                la_ = self._interp.adaptivePredict(self._input,24,self._ctx)
                if la_ == 1:
                    self.state = 396
                    self.match(PowerEventDSLParser.T__5)
                    self.state = 397
                    self.nodeStatement()


                pass
            elif token in [40]:
                self.state = 400
                self.nodeStatement()
                pass
            else:
                raise NoViableAltException(self)

            self.state = 407
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==6:
                self.state = 403
                self.match(PowerEventDSLParser.T__5)
                self.state = 404
                self.networkAdjustmentClause()
                self.state = 409
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class LinkStatementContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def linkClause(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(PowerEventDSLParser.LinkClauseContext)
            else:
                return self.getTypedRuleContext(PowerEventDSLParser.LinkClauseContext,i)


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_linkStatement

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterLinkStatement" ):
                listener.enterLinkStatement(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitLinkStatement" ):
                listener.exitLinkStatement(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitLinkStatement" ):
                return visitor.visitLinkStatement(self)
            else:
                return visitor.visitChildren(self)




    def linkStatement(self):

        localctx = PowerEventDSLParser.LinkStatementContext(self, self._ctx, self.state)
        self.enterRule(localctx, 52, self.RULE_linkStatement)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 410
            self.linkClause()
            self.state = 415
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,27,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    self.state = 411
                    self.match(PowerEventDSLParser.T__5)
                    self.state = 412
                    self.linkClause() 
                self.state = 417
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,27,self._ctx)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class NodeStatementContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def nodeClause(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(PowerEventDSLParser.NodeClauseContext)
            else:
                return self.getTypedRuleContext(PowerEventDSLParser.NodeClauseContext,i)


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_nodeStatement

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterNodeStatement" ):
                listener.enterNodeStatement(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitNodeStatement" ):
                listener.exitNodeStatement(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitNodeStatement" ):
                return visitor.visitNodeStatement(self)
            else:
                return visitor.visitChildren(self)




    def nodeStatement(self):

        localctx = PowerEventDSLParser.NodeStatementContext(self, self._ctx, self.state)
        self.enterRule(localctx, 54, self.RULE_nodeStatement)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 418
            self.nodeClause()
            self.state = 423
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,28,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    self.state = 419
                    self.match(PowerEventDSLParser.T__5)
                    self.state = 420
                    self.nodeClause() 
                self.state = 425
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,28,self._ctx)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class NetworkAdjustmentClauseContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def delayClause(self):
            return self.getTypedRuleContext(PowerEventDSLParser.DelayClauseContext,0)


        def dropClause(self):
            return self.getTypedRuleContext(PowerEventDSLParser.DropClauseContext,0)


        def corruptionClause(self):
            return self.getTypedRuleContext(PowerEventDSLParser.CorruptionClauseContext,0)


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_networkAdjustmentClause

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterNetworkAdjustmentClause" ):
                listener.enterNetworkAdjustmentClause(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitNetworkAdjustmentClause" ):
                listener.exitNetworkAdjustmentClause(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitNetworkAdjustmentClause" ):
                return visitor.visitNetworkAdjustmentClause(self)
            else:
                return visitor.visitChildren(self)




    def networkAdjustmentClause(self):

        localctx = PowerEventDSLParser.NetworkAdjustmentClauseContext(self, self._ctx, self.state)
        self.enterRule(localctx, 56, self.RULE_networkAdjustmentClause)
        try:
            self.state = 429
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [41]:
                self.enterOuterAlt(localctx, 1)
                self.state = 426
                self.delayClause()
                pass
            elif token in [46]:
                self.enterOuterAlt(localctx, 2)
                self.state = 427
                self.dropClause()
                pass
            elif token in [48]:
                self.enterOuterAlt(localctx, 3)
                self.state = 428
                self.corruptionClause()
                pass
            else:
                raise NoViableAltException(self)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class LinkClauseContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def STRING(self, i:int=None):
            if i is None:
                return self.getTokens(PowerEventDSLParser.STRING)
            else:
                return self.getToken(PowerEventDSLParser.STRING, i)

        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_linkClause

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterLinkClause" ):
                listener.enterLinkClause(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitLinkClause" ):
                listener.exitLinkClause(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitLinkClause" ):
                return visitor.visitLinkClause(self)
            else:
                return visitor.visitChildren(self)




    def linkClause(self):

        localctx = PowerEventDSLParser.LinkClauseContext(self, self._ctx, self.state)
        self.enterRule(localctx, 58, self.RULE_linkClause)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 431
            self.match(PowerEventDSLParser.T__37)
            self.state = 432
            self.match(PowerEventDSLParser.T__38)
            self.state = 433
            self.match(PowerEventDSLParser.STRING)
            self.state = 434
            self.match(PowerEventDSLParser.T__9)
            self.state = 435
            self.match(PowerEventDSLParser.STRING)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class NodeClauseContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def STRING(self):
            return self.getToken(PowerEventDSLParser.STRING, 0)

        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_nodeClause

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterNodeClause" ):
                listener.enterNodeClause(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitNodeClause" ):
                listener.exitNodeClause(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitNodeClause" ):
                return visitor.visitNodeClause(self)
            else:
                return visitor.visitChildren(self)




    def nodeClause(self):

        localctx = PowerEventDSLParser.NodeClauseContext(self, self._ctx, self.state)
        self.enterRule(localctx, 60, self.RULE_nodeClause)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 437
            self.match(PowerEventDSLParser.T__39)
            self.state = 438
            self.match(PowerEventDSLParser.STRING)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class DelayClauseContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def delayFunction(self):
            return self.getTypedRuleContext(PowerEventDSLParser.DelayFunctionContext,0)


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_delayClause

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterDelayClause" ):
                listener.enterDelayClause(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitDelayClause" ):
                listener.exitDelayClause(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitDelayClause" ):
                return visitor.visitDelayClause(self)
            else:
                return visitor.visitChildren(self)




    def delayClause(self):

        localctx = PowerEventDSLParser.DelayClauseContext(self, self._ctx, self.state)
        self.enterRule(localctx, 62, self.RULE_delayClause)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 440
            self.match(PowerEventDSLParser.T__40)
            self.state = 441
            self.delayFunction()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class DelayFunctionContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def NUMBER(self, i:int=None):
            if i is None:
                return self.getTokens(PowerEventDSLParser.NUMBER)
            else:
                return self.getToken(PowerEventDSLParser.NUMBER, i)

        def timeUnit(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(PowerEventDSLParser.TimeUnitContext)
            else:
                return self.getTypedRuleContext(PowerEventDSLParser.TimeUnitContext,i)


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_delayFunction

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterDelayFunction" ):
                listener.enterDelayFunction(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitDelayFunction" ):
                listener.exitDelayFunction(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitDelayFunction" ):
                return visitor.visitDelayFunction(self)
            else:
                return visitor.visitChildren(self)




    def delayFunction(self):

        localctx = PowerEventDSLParser.DelayFunctionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 64, self.RULE_delayFunction)
        try:
            self.state = 454
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [42]:
                self.enterOuterAlt(localctx, 1)
                self.state = 443
                self.match(PowerEventDSLParser.T__41)
                self.state = 444
                self.match(PowerEventDSLParser.NUMBER)
                self.state = 445
                self.timeUnit()
                pass
            elif token in [43]:
                self.enterOuterAlt(localctx, 2)
                self.state = 446
                self.match(PowerEventDSLParser.T__42)
                self.state = 447
                self.match(PowerEventDSLParser.T__43)
                self.state = 448
                self.match(PowerEventDSLParser.NUMBER)
                self.state = 449
                self.timeUnit()
                self.state = 450
                self.match(PowerEventDSLParser.T__44)
                self.state = 451
                self.match(PowerEventDSLParser.NUMBER)
                self.state = 452
                self.timeUnit()
                pass
            else:
                raise NoViableAltException(self)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class DropClauseContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def dropFunction(self):
            return self.getTypedRuleContext(PowerEventDSLParser.DropFunctionContext,0)


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_dropClause

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterDropClause" ):
                listener.enterDropClause(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitDropClause" ):
                listener.exitDropClause(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitDropClause" ):
                return visitor.visitDropClause(self)
            else:
                return visitor.visitChildren(self)




    def dropClause(self):

        localctx = PowerEventDSLParser.DropClauseContext(self, self._ctx, self.state)
        self.enterRule(localctx, 66, self.RULE_dropClause)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 456
            self.match(PowerEventDSLParser.T__45)
            self.state = 457
            self.dropFunction()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class DropFunctionContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def booleanLiteral(self):
            return self.getTypedRuleContext(PowerEventDSLParser.BooleanLiteralContext,0)


        def NUMBER(self):
            return self.getToken(PowerEventDSLParser.NUMBER, 0)

        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_dropFunction

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterDropFunction" ):
                listener.enterDropFunction(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitDropFunction" ):
                listener.exitDropFunction(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitDropFunction" ):
                return visitor.visitDropFunction(self)
            else:
                return visitor.visitChildren(self)




    def dropFunction(self):

        localctx = PowerEventDSLParser.DropFunctionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 68, self.RULE_dropFunction)
        try:
            self.state = 463
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [42]:
                self.enterOuterAlt(localctx, 1)
                self.state = 459
                self.match(PowerEventDSLParser.T__41)
                self.state = 460
                self.booleanLiteral()
                pass
            elif token in [47]:
                self.enterOuterAlt(localctx, 2)
                self.state = 461
                self.match(PowerEventDSLParser.T__46)
                self.state = 462
                self.match(PowerEventDSLParser.NUMBER)
                pass
            else:
                raise NoViableAltException(self)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class CorruptionClauseContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def corruptionFunction(self):
            return self.getTypedRuleContext(PowerEventDSLParser.CorruptionFunctionContext,0)


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_corruptionClause

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterCorruptionClause" ):
                listener.enterCorruptionClause(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitCorruptionClause" ):
                listener.exitCorruptionClause(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitCorruptionClause" ):
                return visitor.visitCorruptionClause(self)
            else:
                return visitor.visitChildren(self)




    def corruptionClause(self):

        localctx = PowerEventDSLParser.CorruptionClauseContext(self, self._ctx, self.state)
        self.enterRule(localctx, 70, self.RULE_corruptionClause)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 465
            self.match(PowerEventDSLParser.T__47)
            self.state = 466
            self.corruptionFunction()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class CorruptionFunctionContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def NUMBER(self):
            return self.getToken(PowerEventDSLParser.NUMBER, 0)

        def corruptionNoiseParams(self):
            return self.getTypedRuleContext(PowerEventDSLParser.CorruptionNoiseParamsContext,0)


        def corruptionZeroParams(self):
            return self.getTypedRuleContext(PowerEventDSLParser.CorruptionZeroParamsContext,0)


        def corruptionShiftParams(self):
            return self.getTypedRuleContext(PowerEventDSLParser.CorruptionShiftParamsContext,0)


        def corruptionInvertParams(self):
            return self.getTypedRuleContext(PowerEventDSLParser.CorruptionInvertParamsContext,0)


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_corruptionFunction

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterCorruptionFunction" ):
                listener.enterCorruptionFunction(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitCorruptionFunction" ):
                listener.exitCorruptionFunction(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitCorruptionFunction" ):
                return visitor.visitCorruptionFunction(self)
            else:
                return visitor.visitChildren(self)




    def corruptionFunction(self):

        localctx = PowerEventDSLParser.CorruptionFunctionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 72, self.RULE_corruptionFunction)
        self._la = 0 # Token type
        try:
            self.state = 483
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [49]:
                self.enterOuterAlt(localctx, 1)
                self.state = 468
                self.match(PowerEventDSLParser.T__48)
                self.state = 471
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==50:
                    self.state = 469
                    self.match(PowerEventDSLParser.T__49)
                    self.state = 470
                    self.match(PowerEventDSLParser.NUMBER)


                pass
            elif token in [51]:
                self.enterOuterAlt(localctx, 2)
                self.state = 473
                self.match(PowerEventDSLParser.T__50)
                self.state = 474
                self.corruptionNoiseParams()
                pass
            elif token in [52]:
                self.enterOuterAlt(localctx, 3)
                self.state = 475
                self.match(PowerEventDSLParser.T__51)
                self.state = 476
                self.corruptionNoiseParams()
                pass
            elif token in [53]:
                self.enterOuterAlt(localctx, 4)
                self.state = 477
                self.match(PowerEventDSLParser.T__52)
                self.state = 478
                self.corruptionZeroParams()
                pass
            elif token in [54]:
                self.enterOuterAlt(localctx, 5)
                self.state = 479
                self.match(PowerEventDSLParser.T__53)
                self.state = 480
                self.corruptionShiftParams()
                pass
            elif token in [55]:
                self.enterOuterAlt(localctx, 6)
                self.state = 481
                self.match(PowerEventDSLParser.T__54)
                self.state = 482
                self.corruptionInvertParams()
                pass
            else:
                raise NoViableAltException(self)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class CorruptionNoiseParamsContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def NUMBER(self, i:int=None):
            if i is None:
                return self.getTokens(PowerEventDSLParser.NUMBER)
            else:
                return self.getToken(PowerEventDSLParser.NUMBER, i)

        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_corruptionNoiseParams

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterCorruptionNoiseParams" ):
                listener.enterCorruptionNoiseParams(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitCorruptionNoiseParams" ):
                listener.exitCorruptionNoiseParams(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitCorruptionNoiseParams" ):
                return visitor.visitCorruptionNoiseParams(self)
            else:
                return visitor.visitChildren(self)




    def corruptionNoiseParams(self):

        localctx = PowerEventDSLParser.CorruptionNoiseParamsContext(self, self._ctx, self.state)
        self.enterRule(localctx, 74, self.RULE_corruptionNoiseParams)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 487
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==50:
                self.state = 485
                self.match(PowerEventDSLParser.T__49)
                self.state = 486
                self.match(PowerEventDSLParser.NUMBER)


            self.state = 489
            self.match(PowerEventDSLParser.T__55)
            self.state = 490
            self.match(PowerEventDSLParser.NUMBER)
            self.state = 491
            self.match(PowerEventDSLParser.T__9)
            self.state = 492
            self.match(PowerEventDSLParser.NUMBER)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class CorruptionZeroParamsContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def NUMBER(self, i:int=None):
            if i is None:
                return self.getTokens(PowerEventDSLParser.NUMBER)
            else:
                return self.getToken(PowerEventDSLParser.NUMBER, i)

        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_corruptionZeroParams

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterCorruptionZeroParams" ):
                listener.enterCorruptionZeroParams(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitCorruptionZeroParams" ):
                listener.exitCorruptionZeroParams(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitCorruptionZeroParams" ):
                return visitor.visitCorruptionZeroParams(self)
            else:
                return visitor.visitChildren(self)




    def corruptionZeroParams(self):

        localctx = PowerEventDSLParser.CorruptionZeroParamsContext(self, self._ctx, self.state)
        self.enterRule(localctx, 76, self.RULE_corruptionZeroParams)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 496
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==50:
                self.state = 494
                self.match(PowerEventDSLParser.T__49)
                self.state = 495
                self.match(PowerEventDSLParser.NUMBER)


            self.state = 500
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==57:
                self.state = 498
                self.match(PowerEventDSLParser.T__56)
                self.state = 499
                self.match(PowerEventDSLParser.NUMBER)


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class CorruptionShiftParamsContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def NUMBER(self, i:int=None):
            if i is None:
                return self.getTokens(PowerEventDSLParser.NUMBER)
            else:
                return self.getToken(PowerEventDSLParser.NUMBER, i)

        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_corruptionShiftParams

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterCorruptionShiftParams" ):
                listener.enterCorruptionShiftParams(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitCorruptionShiftParams" ):
                listener.exitCorruptionShiftParams(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitCorruptionShiftParams" ):
                return visitor.visitCorruptionShiftParams(self)
            else:
                return visitor.visitChildren(self)




    def corruptionShiftParams(self):

        localctx = PowerEventDSLParser.CorruptionShiftParamsContext(self, self._ctx, self.state)
        self.enterRule(localctx, 78, self.RULE_corruptionShiftParams)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 504
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==50:
                self.state = 502
                self.match(PowerEventDSLParser.T__49)
                self.state = 503
                self.match(PowerEventDSLParser.NUMBER)


            self.state = 506
            self.match(PowerEventDSLParser.T__29)
            self.state = 507
            self.match(PowerEventDSLParser.NUMBER)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class CorruptionInvertParamsContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def NUMBER(self, i:int=None):
            if i is None:
                return self.getTokens(PowerEventDSLParser.NUMBER)
            else:
                return self.getToken(PowerEventDSLParser.NUMBER, i)

        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_corruptionInvertParams

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterCorruptionInvertParams" ):
                listener.enterCorruptionInvertParams(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitCorruptionInvertParams" ):
                listener.exitCorruptionInvertParams(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitCorruptionInvertParams" ):
                return visitor.visitCorruptionInvertParams(self)
            else:
                return visitor.visitChildren(self)




    def corruptionInvertParams(self):

        localctx = PowerEventDSLParser.CorruptionInvertParamsContext(self, self._ctx, self.state)
        self.enterRule(localctx, 80, self.RULE_corruptionInvertParams)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 511
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==50:
                self.state = 509
                self.match(PowerEventDSLParser.T__49)
                self.state = 510
                self.match(PowerEventDSLParser.NUMBER)


            self.state = 515
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==30:
                self.state = 513
                self.match(PowerEventDSLParser.T__29)
                self.state = 514
                self.match(PowerEventDSLParser.NUMBER)


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ComponentContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def componentType(self):
            return self.getTypedRuleContext(PowerEventDSLParser.ComponentTypeContext,0)


        def stringAtom(self):
            return self.getTypedRuleContext(PowerEventDSLParser.StringAtomContext,0)


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_component

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterComponent" ):
                listener.enterComponent(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitComponent" ):
                listener.exitComponent(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitComponent" ):
                return visitor.visitComponent(self)
            else:
                return visitor.visitChildren(self)




    def component(self):

        localctx = PowerEventDSLParser.ComponentContext(self, self._ctx, self.state)
        self.enterRule(localctx, 82, self.RULE_component)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 517
            self.componentType()
            self.state = 518
            self.stringAtom()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ComponentTypeContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_componentType

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterComponentType" ):
                listener.enterComponentType(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitComponentType" ):
                listener.exitComponentType(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitComponentType" ):
                return visitor.visitComponentType(self)
            else:
                return visitor.visitChildren(self)




    def componentType(self):

        localctx = PowerEventDSLParser.ComponentTypeContext(self, self._ctx, self.state)
        self.enterRule(localctx, 84, self.RULE_componentType)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 520
            _la = self._input.LA(1)
            if not(((((_la - 25)) & ~0x3f) == 0 and ((1 << (_la - 25)) & 70360154243155) != 0)):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class TargetContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def stringAtom(self):
            return self.getTypedRuleContext(PowerEventDSLParser.StringAtomContext,0)


        def listSpec(self):
            return self.getTypedRuleContext(PowerEventDSLParser.ListSpecContext,0)


        def clusterSpec(self):
            return self.getTypedRuleContext(PowerEventDSLParser.ClusterSpecContext,0)


        def dynamicClusterSpec(self):
            return self.getTypedRuleContext(PowerEventDSLParser.DynamicClusterSpecContext,0)


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_target

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterTarget" ):
                listener.enterTarget(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitTarget" ):
                listener.exitTarget(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitTarget" ):
                return visitor.visitTarget(self)
            else:
                return visitor.visitChildren(self)




    def target(self):

        localctx = PowerEventDSLParser.TargetContext(self, self._ctx, self.state)
        self.enterRule(localctx, 86, self.RULE_target)
        try:
            self.state = 526
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [120, 121]:
                self.enterOuterAlt(localctx, 1)
                self.state = 522
                self.stringAtom()
                pass
            elif token in [71]:
                self.enterOuterAlt(localctx, 2)
                self.state = 523
                self.listSpec()
                pass
            elif token in [73]:
                self.enterOuterAlt(localctx, 3)
                self.state = 524
                self.clusterSpec()
                pass
            elif token in [74]:
                self.enterOuterAlt(localctx, 4)
                self.state = 525
                self.dynamicClusterSpec()
                pass
            else:
                raise NoViableAltException(self)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ListSpecContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def listItem(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(PowerEventDSLParser.ListItemContext)
            else:
                return self.getTypedRuleContext(PowerEventDSLParser.ListItemContext,i)


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_listSpec

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterListSpec" ):
                listener.enterListSpec(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitListSpec" ):
                listener.exitListSpec(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitListSpec" ):
                return visitor.visitListSpec(self)
            else:
                return visitor.visitChildren(self)




    def listSpec(self):

        localctx = PowerEventDSLParser.ListSpecContext(self, self._ctx, self.state)
        self.enterRule(localctx, 88, self.RULE_listSpec)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 528
            self.match(PowerEventDSLParser.T__70)
            self.state = 529
            self.listItem()
            self.state = 534
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==6:
                self.state = 530
                self.match(PowerEventDSLParser.T__5)
                self.state = 531
                self.listItem()
                self.state = 536
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 537
            self.match(PowerEventDSLParser.T__71)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ListItemContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def stringAtom(self):
            return self.getTypedRuleContext(PowerEventDSLParser.StringAtomContext,0)


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_listItem

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterListItem" ):
                listener.enterListItem(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitListItem" ):
                listener.exitListItem(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitListItem" ):
                return visitor.visitListItem(self)
            else:
                return visitor.visitChildren(self)




    def listItem(self):

        localctx = PowerEventDSLParser.ListItemContext(self, self._ctx, self.state)
        self.enterRule(localctx, 90, self.RULE_listItem)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 539
            self.stringAtom()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ClusterSpecContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def listSpec(self):
            return self.getTypedRuleContext(PowerEventDSLParser.ListSpecContext,0)


        def stringAtom(self):
            return self.getTypedRuleContext(PowerEventDSLParser.StringAtomContext,0)


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_clusterSpec

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterClusterSpec" ):
                listener.enterClusterSpec(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitClusterSpec" ):
                listener.exitClusterSpec(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitClusterSpec" ):
                return visitor.visitClusterSpec(self)
            else:
                return visitor.visitChildren(self)




    def clusterSpec(self):

        localctx = PowerEventDSLParser.ClusterSpecContext(self, self._ctx, self.state)
        self.enterRule(localctx, 92, self.RULE_clusterSpec)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 541
            self.match(PowerEventDSLParser.T__72)
            self.state = 543
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==120 or _la==121:
                self.state = 542
                self.stringAtom()


            self.state = 545
            self.listSpec()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class DynamicClusterSpecContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def relationshipSpec(self):
            return self.getTypedRuleContext(PowerEventDSLParser.RelationshipSpecContext,0)


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_dynamicClusterSpec

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterDynamicClusterSpec" ):
                listener.enterDynamicClusterSpec(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitDynamicClusterSpec" ):
                listener.exitDynamicClusterSpec(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitDynamicClusterSpec" ):
                return visitor.visitDynamicClusterSpec(self)
            else:
                return visitor.visitChildren(self)




    def dynamicClusterSpec(self):

        localctx = PowerEventDSLParser.DynamicClusterSpecContext(self, self._ctx, self.state)
        self.enterRule(localctx, 94, self.RULE_dynamicClusterSpec)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 547
            self.match(PowerEventDSLParser.T__73)
            self.state = 548
            self.match(PowerEventDSLParser.T__72)
            self.state = 549
            self.relationshipSpec()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ChannelSpecContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_channelSpec

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterChannelSpec" ):
                listener.enterChannelSpec(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitChannelSpec" ):
                listener.exitChannelSpec(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitChannelSpec" ):
                return visitor.visitChannelSpec(self)
            else:
                return visitor.visitChildren(self)




    def channelSpec(self):

        localctx = PowerEventDSLParser.ChannelSpecContext(self, self._ctx, self.state)
        self.enterRule(localctx, 96, self.RULE_channelSpec)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 551
            _la = self._input.LA(1)
            if not(((((_la - 75)) & ~0x3f) == 0 and ((1 << (_la - 75)) & 15) != 0)):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class SetRangeContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def signedNumber(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(PowerEventDSLParser.SignedNumberContext)
            else:
                return self.getTypedRuleContext(PowerEventDSLParser.SignedNumberContext,i)


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_setRange

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterSetRange" ):
                listener.enterSetRange(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitSetRange" ):
                listener.exitSetRange(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSetRange" ):
                return visitor.visitSetRange(self)
            else:
                return visitor.visitChildren(self)




    def setRange(self):

        localctx = PowerEventDSLParser.SetRangeContext(self, self._ctx, self.state)
        self.enterRule(localctx, 98, self.RULE_setRange)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 555
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==39:
                self.state = 553
                self.match(PowerEventDSLParser.T__38)
                self.state = 554
                self.signedNumber()


            self.state = 557
            self.match(PowerEventDSLParser.T__9)
            self.state = 558
            self.signedNumber()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class SignedNumberContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def signedNumericAtom(self):
            return self.getTypedRuleContext(PowerEventDSLParser.SignedNumericAtomContext,0)


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_signedNumber

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterSignedNumber" ):
                listener.enterSignedNumber(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitSignedNumber" ):
                listener.exitSignedNumber(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSignedNumber" ):
                return visitor.visitSignedNumber(self)
            else:
                return visitor.visitChildren(self)




    def signedNumber(self):

        localctx = PowerEventDSLParser.SignedNumberContext(self, self._ctx, self.state)
        self.enterRule(localctx, 100, self.RULE_signedNumber)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 560
            self.signedNumericAtom()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class SignedNumericAtomContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def numericAtom(self):
            return self.getTypedRuleContext(PowerEventDSLParser.NumericAtomContext,0)


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_signedNumericAtom

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterSignedNumericAtom" ):
                listener.enterSignedNumericAtom(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitSignedNumericAtom" ):
                listener.exitSignedNumericAtom(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSignedNumericAtom" ):
                return visitor.visitSignedNumericAtom(self)
            else:
                return visitor.visitChildren(self)




    def signedNumericAtom(self):

        localctx = PowerEventDSLParser.SignedNumericAtomContext(self, self._ctx, self.state)
        self.enterRule(localctx, 102, self.RULE_signedNumericAtom)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 563
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==79 or _la==80:
                self.state = 562
                _la = self._input.LA(1)
                if not(_la==79 or _la==80):
                    self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()


            self.state = 565
            self.numericAtom()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class StringAtomContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def STRING(self):
            return self.getToken(PowerEventDSLParser.STRING, 0)

        def IDENTIFIER(self):
            return self.getToken(PowerEventDSLParser.IDENTIFIER, 0)

        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_stringAtom

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterStringAtom" ):
                listener.enterStringAtom(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitStringAtom" ):
                listener.exitStringAtom(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitStringAtom" ):
                return visitor.visitStringAtom(self)
            else:
                return visitor.visitChildren(self)




    def stringAtom(self):

        localctx = PowerEventDSLParser.StringAtomContext(self, self._ctx, self.state)
        self.enterRule(localctx, 104, self.RULE_stringAtom)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 567
            _la = self._input.LA(1)
            if not(_la==120 or _la==121):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class NumericAtomContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def NUMBER(self):
            return self.getToken(PowerEventDSLParser.NUMBER, 0)

        def IDENTIFIER(self):
            return self.getToken(PowerEventDSLParser.IDENTIFIER, 0)

        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_numericAtom

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterNumericAtom" ):
                listener.enterNumericAtom(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitNumericAtom" ):
                listener.exitNumericAtom(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitNumericAtom" ):
                return visitor.visitNumericAtom(self)
            else:
                return visitor.visitChildren(self)




    def numericAtom(self):

        localctx = PowerEventDSLParser.NumericAtomContext(self, self._ctx, self.state)
        self.enterRule(localctx, 106, self.RULE_numericAtom)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 569
            _la = self._input.LA(1)
            if not(_la==118 or _la==121):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class RelationshipSpecContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def regexFilter(self):
            return self.getTypedRuleContext(PowerEventDSLParser.RegexFilterContext,0)


        def groupByFilter(self):
            return self.getTypedRuleContext(PowerEventDSLParser.GroupByFilterContext,0)


        def propertyFilter(self):
            return self.getTypedRuleContext(PowerEventDSLParser.PropertyFilterContext,0)


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_relationshipSpec

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterRelationshipSpec" ):
                listener.enterRelationshipSpec(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitRelationshipSpec" ):
                listener.exitRelationshipSpec(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitRelationshipSpec" ):
                return visitor.visitRelationshipSpec(self)
            else:
                return visitor.visitChildren(self)




    def relationshipSpec(self):

        localctx = PowerEventDSLParser.RelationshipSpecContext(self, self._ctx, self.state)
        self.enterRule(localctx, 108, self.RULE_relationshipSpec)
        try:
            self.state = 574
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [81]:
                self.enterOuterAlt(localctx, 1)
                self.state = 571
                self.regexFilter()
                pass
            elif token in [83]:
                self.enterOuterAlt(localctx, 2)
                self.state = 572
                self.groupByFilter()
                pass
            elif token in [84]:
                self.enterOuterAlt(localctx, 3)
                self.state = 573
                self.propertyFilter()
                pass
            else:
                raise NoViableAltException(self)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class RegexFilterContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def stringAtom(self):
            return self.getTypedRuleContext(PowerEventDSLParser.StringAtomContext,0)


        def componentType(self):
            return self.getTypedRuleContext(PowerEventDSLParser.ComponentTypeContext,0)


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_regexFilter

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterRegexFilter" ):
                listener.enterRegexFilter(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitRegexFilter" ):
                listener.exitRegexFilter(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitRegexFilter" ):
                return visitor.visitRegexFilter(self)
            else:
                return visitor.visitChildren(self)




    def regexFilter(self):

        localctx = PowerEventDSLParser.RegexFilterContext(self, self._ctx, self.state)
        self.enterRule(localctx, 110, self.RULE_regexFilter)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 576
            self.match(PowerEventDSLParser.T__80)
            self.state = 577
            self.stringAtom()
            self.state = 578
            self.match(PowerEventDSLParser.T__81)
            self.state = 579
            self.componentType()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class GroupByFilterContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def propertyName(self):
            return self.getTypedRuleContext(PowerEventDSLParser.PropertyNameContext,0)


        def stringAtom(self):
            return self.getTypedRuleContext(PowerEventDSLParser.StringAtomContext,0)


        def componentType(self):
            return self.getTypedRuleContext(PowerEventDSLParser.ComponentTypeContext,0)


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_groupByFilter

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterGroupByFilter" ):
                listener.enterGroupByFilter(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitGroupByFilter" ):
                listener.exitGroupByFilter(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitGroupByFilter" ):
                return visitor.visitGroupByFilter(self)
            else:
                return visitor.visitChildren(self)




    def groupByFilter(self):

        localctx = PowerEventDSLParser.GroupByFilterContext(self, self._ctx, self.state)
        self.enterRule(localctx, 112, self.RULE_groupByFilter)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 581
            self.match(PowerEventDSLParser.T__82)
            self.state = 582
            self.match(PowerEventDSLParser.T__29)
            self.state = 583
            self.propertyName()
            self.state = 584
            self.stringAtom()
            self.state = 585
            self.match(PowerEventDSLParser.T__81)
            self.state = 586
            self.componentType()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class PropertyFilterContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def propertyName(self):
            return self.getTypedRuleContext(PowerEventDSLParser.PropertyNameContext,0)


        def comparison(self):
            return self.getTypedRuleContext(PowerEventDSLParser.ComparisonContext,0)


        def numericAtom(self):
            return self.getTypedRuleContext(PowerEventDSLParser.NumericAtomContext,0)


        def componentType(self):
            return self.getTypedRuleContext(PowerEventDSLParser.ComponentTypeContext,0)


        def unit(self):
            return self.getTypedRuleContext(PowerEventDSLParser.UnitContext,0)


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_propertyFilter

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterPropertyFilter" ):
                listener.enterPropertyFilter(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitPropertyFilter" ):
                listener.exitPropertyFilter(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitPropertyFilter" ):
                return visitor.visitPropertyFilter(self)
            else:
                return visitor.visitChildren(self)




    def propertyFilter(self):

        localctx = PowerEventDSLParser.PropertyFilterContext(self, self._ctx, self.state)
        self.enterRule(localctx, 114, self.RULE_propertyFilter)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 588
            self.match(PowerEventDSLParser.T__83)
            self.state = 589
            self.propertyName()
            self.state = 590
            self.comparison()
            self.state = 591
            self.numericAtom()
            self.state = 593
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if ((((_la - 113)) & ~0x3f) == 0 and ((1 << (_la - 113)) & 31) != 0):
                self.state = 592
                self.unit()


            self.state = 595
            self.match(PowerEventDSLParser.T__81)
            self.state = 596
            self.componentType()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class PropertyNameContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def stringAtom(self):
            return self.getTypedRuleContext(PowerEventDSLParser.StringAtomContext,0)


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_propertyName

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterPropertyName" ):
                listener.enterPropertyName(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitPropertyName" ):
                listener.exitPropertyName(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitPropertyName" ):
                return visitor.visitPropertyName(self)
            else:
                return visitor.visitChildren(self)




    def propertyName(self):

        localctx = PowerEventDSLParser.PropertyNameContext(self, self._ctx, self.state)
        self.enterRule(localctx, 116, self.RULE_propertyName)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 598
            self.stringAtom()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class TimeValueContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def numericAtom(self):
            return self.getTypedRuleContext(PowerEventDSLParser.NumericAtomContext,0)


        def timeUnit(self):
            return self.getTypedRuleContext(PowerEventDSLParser.TimeUnitContext,0)


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_timeValue

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterTimeValue" ):
                listener.enterTimeValue(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitTimeValue" ):
                listener.exitTimeValue(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitTimeValue" ):
                return visitor.visitTimeValue(self)
            else:
                return visitor.visitChildren(self)




    def timeValue(self):

        localctx = PowerEventDSLParser.TimeValueContext(self, self._ctx, self.state)
        self.enterRule(localctx, 118, self.RULE_timeValue)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 600
            self.numericAtom()
            self.state = 601
            self.timeUnit()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class TimeUnitContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_timeUnit

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterTimeUnit" ):
                listener.enterTimeUnit(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitTimeUnit" ):
                listener.exitTimeUnit(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitTimeUnit" ):
                return visitor.visitTimeUnit(self)
            else:
                return visitor.visitChildren(self)




    def timeUnit(self):

        localctx = PowerEventDSLParser.TimeUnitContext(self, self._ctx, self.state)
        self.enterRule(localctx, 120, self.RULE_timeUnit)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 603
            _la = self._input.LA(1)
            if not(((((_la - 85)) & ~0x3f) == 0 and ((1 << (_la - 85)) & 63) != 0)):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class TimeSpecContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def timeExpr(self):
            return self.getTypedRuleContext(PowerEventDSLParser.TimeExprContext,0)


        def intervalSpec(self):
            return self.getTypedRuleContext(PowerEventDSLParser.IntervalSpecContext,0)


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_timeSpec

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterTimeSpec" ):
                listener.enterTimeSpec(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitTimeSpec" ):
                listener.exitTimeSpec(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitTimeSpec" ):
                return visitor.visitTimeSpec(self)
            else:
                return visitor.visitChildren(self)




    def timeSpec(self):

        localctx = PowerEventDSLParser.TimeSpecContext(self, self._ctx, self.state)
        self.enterRule(localctx, 122, self.RULE_timeSpec)
        try:
            self.state = 607
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [91, 118, 121]:
                self.enterOuterAlt(localctx, 1)
                self.state = 605
                self.timeExpr()
                pass
            elif token in [71]:
                self.enterOuterAlt(localctx, 2)
                self.state = 606
                self.intervalSpec()
                pass
            else:
                raise NoViableAltException(self)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class TimeExprContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def timeValue(self):
            return self.getTypedRuleContext(PowerEventDSLParser.TimeValueContext,0)


        def nowExpr(self):
            return self.getTypedRuleContext(PowerEventDSLParser.NowExprContext,0)


        def IDENTIFIER(self):
            return self.getToken(PowerEventDSLParser.IDENTIFIER, 0)

        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_timeExpr

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterTimeExpr" ):
                listener.enterTimeExpr(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitTimeExpr" ):
                listener.exitTimeExpr(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitTimeExpr" ):
                return visitor.visitTimeExpr(self)
            else:
                return visitor.visitChildren(self)




    def timeExpr(self):

        localctx = PowerEventDSLParser.TimeExprContext(self, self._ctx, self.state)
        self.enterRule(localctx, 124, self.RULE_timeExpr)
        try:
            self.state = 612
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,48,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 609
                self.timeValue()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 610
                self.nowExpr()
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 611
                self.match(PowerEventDSLParser.IDENTIFIER)
                pass


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class NowExprContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def timeValue(self):
            return self.getTypedRuleContext(PowerEventDSLParser.TimeValueContext,0)


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_nowExpr

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterNowExpr" ):
                listener.enterNowExpr(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitNowExpr" ):
                listener.exitNowExpr(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitNowExpr" ):
                return visitor.visitNowExpr(self)
            else:
                return visitor.visitChildren(self)




    def nowExpr(self):

        localctx = PowerEventDSLParser.NowExprContext(self, self._ctx, self.state)
        self.enterRule(localctx, 126, self.RULE_nowExpr)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 614
            self.match(PowerEventDSLParser.T__90)
            self.state = 617
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==79 or _la==80:
                self.state = 615
                _la = self._input.LA(1)
                if not(_la==79 or _la==80):
                    self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 616
                self.timeValue()


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class IntervalSpecContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def timeExpr(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(PowerEventDSLParser.TimeExprContext)
            else:
                return self.getTypedRuleContext(PowerEventDSLParser.TimeExprContext,i)


        def lawSpec(self):
            return self.getTypedRuleContext(PowerEventDSLParser.LawSpecContext,0)


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_intervalSpec

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterIntervalSpec" ):
                listener.enterIntervalSpec(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitIntervalSpec" ):
                listener.exitIntervalSpec(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitIntervalSpec" ):
                return visitor.visitIntervalSpec(self)
            else:
                return visitor.visitChildren(self)




    def intervalSpec(self):

        localctx = PowerEventDSLParser.IntervalSpecContext(self, self._ctx, self.state)
        self.enterRule(localctx, 128, self.RULE_intervalSpec)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 619
            self.match(PowerEventDSLParser.T__70)
            self.state = 620
            self.timeExpr()
            self.state = 621
            self.match(PowerEventDSLParser.T__5)
            self.state = 622
            self.timeExpr()
            self.state = 623
            self.match(PowerEventDSLParser.T__71)
            self.state = 627
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==92:
                self.state = 624
                self.match(PowerEventDSLParser.T__91)
                self.state = 625
                self.match(PowerEventDSLParser.T__92)
                self.state = 626
                self.lawSpec()


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class RelativeTimeSpecContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def relativeTimeExpr(self):
            return self.getTypedRuleContext(PowerEventDSLParser.RelativeTimeExprContext,0)


        def relativeIntervalSpec(self):
            return self.getTypedRuleContext(PowerEventDSLParser.RelativeIntervalSpecContext,0)


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_relativeTimeSpec

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterRelativeTimeSpec" ):
                listener.enterRelativeTimeSpec(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitRelativeTimeSpec" ):
                listener.exitRelativeTimeSpec(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitRelativeTimeSpec" ):
                return visitor.visitRelativeTimeSpec(self)
            else:
                return visitor.visitChildren(self)




    def relativeTimeSpec(self):

        localctx = PowerEventDSLParser.RelativeTimeSpecContext(self, self._ctx, self.state)
        self.enterRule(localctx, 130, self.RULE_relativeTimeSpec)
        try:
            self.state = 631
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [79, 80, 118, 121]:
                self.enterOuterAlt(localctx, 1)
                self.state = 629
                self.relativeTimeExpr()
                pass
            elif token in [71]:
                self.enterOuterAlt(localctx, 2)
                self.state = 630
                self.relativeIntervalSpec()
                pass
            else:
                raise NoViableAltException(self)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class RelativeTimeExprContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def relativeTimeValue(self):
            return self.getTypedRuleContext(PowerEventDSLParser.RelativeTimeValueContext,0)


        def IDENTIFIER(self):
            return self.getToken(PowerEventDSLParser.IDENTIFIER, 0)

        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_relativeTimeExpr

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterRelativeTimeExpr" ):
                listener.enterRelativeTimeExpr(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitRelativeTimeExpr" ):
                listener.exitRelativeTimeExpr(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitRelativeTimeExpr" ):
                return visitor.visitRelativeTimeExpr(self)
            else:
                return visitor.visitChildren(self)




    def relativeTimeExpr(self):

        localctx = PowerEventDSLParser.RelativeTimeExprContext(self, self._ctx, self.state)
        self.enterRule(localctx, 132, self.RULE_relativeTimeExpr)
        try:
            self.state = 635
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,52,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 633
                self.relativeTimeValue()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 634
                self.match(PowerEventDSLParser.IDENTIFIER)
                pass


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class RelativeTimeValueContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def signedNumericAtom(self):
            return self.getTypedRuleContext(PowerEventDSLParser.SignedNumericAtomContext,0)


        def timeUnit(self):
            return self.getTypedRuleContext(PowerEventDSLParser.TimeUnitContext,0)


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_relativeTimeValue

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterRelativeTimeValue" ):
                listener.enterRelativeTimeValue(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitRelativeTimeValue" ):
                listener.exitRelativeTimeValue(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitRelativeTimeValue" ):
                return visitor.visitRelativeTimeValue(self)
            else:
                return visitor.visitChildren(self)




    def relativeTimeValue(self):

        localctx = PowerEventDSLParser.RelativeTimeValueContext(self, self._ctx, self.state)
        self.enterRule(localctx, 134, self.RULE_relativeTimeValue)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 637
            self.signedNumericAtom()
            self.state = 638
            self.timeUnit()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class RelativeIntervalSpecContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def relativeTimeExpr(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(PowerEventDSLParser.RelativeTimeExprContext)
            else:
                return self.getTypedRuleContext(PowerEventDSLParser.RelativeTimeExprContext,i)


        def lawSpec(self):
            return self.getTypedRuleContext(PowerEventDSLParser.LawSpecContext,0)


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_relativeIntervalSpec

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterRelativeIntervalSpec" ):
                listener.enterRelativeIntervalSpec(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitRelativeIntervalSpec" ):
                listener.exitRelativeIntervalSpec(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitRelativeIntervalSpec" ):
                return visitor.visitRelativeIntervalSpec(self)
            else:
                return visitor.visitChildren(self)




    def relativeIntervalSpec(self):

        localctx = PowerEventDSLParser.RelativeIntervalSpecContext(self, self._ctx, self.state)
        self.enterRule(localctx, 136, self.RULE_relativeIntervalSpec)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 640
            self.match(PowerEventDSLParser.T__70)
            self.state = 641
            self.relativeTimeExpr()
            self.state = 642
            self.match(PowerEventDSLParser.T__5)
            self.state = 643
            self.relativeTimeExpr()
            self.state = 644
            self.match(PowerEventDSLParser.T__71)
            self.state = 648
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==92:
                self.state = 645
                self.match(PowerEventDSLParser.T__91)
                self.state = 646
                self.match(PowerEventDSLParser.T__92)
                self.state = 647
                self.lawSpec()


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class LawSpecContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def STRING(self):
            return self.getToken(PowerEventDSLParser.STRING, 0)

        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_lawSpec

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterLawSpec" ):
                listener.enterLawSpec(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitLawSpec" ):
                listener.exitLawSpec(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitLawSpec" ):
                return visitor.visitLawSpec(self)
            else:
                return visitor.visitChildren(self)




    def lawSpec(self):

        localctx = PowerEventDSLParser.LawSpecContext(self, self._ctx, self.state)
        self.enterRule(localctx, 138, self.RULE_lawSpec)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 650
            _la = self._input.LA(1)
            if not(_la==94 or _la==120):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class DynamicExpressionContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def expression(self):
            return self.getTypedRuleContext(PowerEventDSLParser.ExpressionContext,0)


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_dynamicExpression

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterDynamicExpression" ):
                listener.enterDynamicExpression(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitDynamicExpression" ):
                listener.exitDynamicExpression(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitDynamicExpression" ):
                return visitor.visitDynamicExpression(self)
            else:
                return visitor.visitChildren(self)




    def dynamicExpression(self):

        localctx = PowerEventDSLParser.DynamicExpressionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 140, self.RULE_dynamicExpression)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 652
            self.expression()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ExpressionContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def booleanExpr(self):
            return self.getTypedRuleContext(PowerEventDSLParser.BooleanExprContext,0)


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_expression

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterExpression" ):
                listener.enterExpression(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitExpression" ):
                listener.exitExpression(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitExpression" ):
                return visitor.visitExpression(self)
            else:
                return visitor.visitChildren(self)




    def expression(self):

        localctx = PowerEventDSLParser.ExpressionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 142, self.RULE_expression)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 654
            self.booleanExpr()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class BooleanExprContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def booleanTerm(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(PowerEventDSLParser.BooleanTermContext)
            else:
                return self.getTypedRuleContext(PowerEventDSLParser.BooleanTermContext,i)


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_booleanExpr

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterBooleanExpr" ):
                listener.enterBooleanExpr(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitBooleanExpr" ):
                listener.exitBooleanExpr(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitBooleanExpr" ):
                return visitor.visitBooleanExpr(self)
            else:
                return visitor.visitChildren(self)




    def booleanExpr(self):

        localctx = PowerEventDSLParser.BooleanExprContext(self, self._ctx, self.state)
        self.enterRule(localctx, 144, self.RULE_booleanExpr)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 656
            self.booleanTerm()
            self.state = 661
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==95:
                self.state = 657
                self.match(PowerEventDSLParser.T__94)
                self.state = 658
                self.booleanTerm()
                self.state = 663
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class BooleanTermContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def booleanFactor(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(PowerEventDSLParser.BooleanFactorContext)
            else:
                return self.getTypedRuleContext(PowerEventDSLParser.BooleanFactorContext,i)


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_booleanTerm

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterBooleanTerm" ):
                listener.enterBooleanTerm(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitBooleanTerm" ):
                listener.exitBooleanTerm(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitBooleanTerm" ):
                return visitor.visitBooleanTerm(self)
            else:
                return visitor.visitChildren(self)




    def booleanTerm(self):

        localctx = PowerEventDSLParser.BooleanTermContext(self, self._ctx, self.state)
        self.enterRule(localctx, 146, self.RULE_booleanTerm)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 664
            self.booleanFactor()
            self.state = 669
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==96:
                self.state = 665
                self.match(PowerEventDSLParser.T__95)
                self.state = 666
                self.booleanFactor()
                self.state = 671
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class BooleanFactorContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def booleanAtomic(self):
            return self.getTypedRuleContext(PowerEventDSLParser.BooleanAtomicContext,0)


        def booleanExpr(self):
            return self.getTypedRuleContext(PowerEventDSLParser.BooleanExprContext,0)


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_booleanFactor

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterBooleanFactor" ):
                listener.enterBooleanFactor(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitBooleanFactor" ):
                listener.exitBooleanFactor(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitBooleanFactor" ):
                return visitor.visitBooleanFactor(self)
            else:
                return visitor.visitChildren(self)




    def booleanFactor(self):

        localctx = PowerEventDSLParser.BooleanFactorContext(self, self._ctx, self.state)
        self.enterRule(localctx, 148, self.RULE_booleanFactor)
        try:
            self.state = 677
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,56,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 672
                self.booleanAtomic()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 673
                self.match(PowerEventDSLParser.T__1)
                self.state = 674
                self.booleanExpr()
                self.state = 675
                self.match(PowerEventDSLParser.T__2)
                pass


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class BooleanAtomicContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def comparisonExpr(self):
            return self.getTypedRuleContext(PowerEventDSLParser.ComparisonExprContext,0)


        def booleanLiteral(self):
            return self.getTypedRuleContext(PowerEventDSLParser.BooleanLiteralContext,0)


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_booleanAtomic

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterBooleanAtomic" ):
                listener.enterBooleanAtomic(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitBooleanAtomic" ):
                listener.exitBooleanAtomic(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitBooleanAtomic" ):
                return visitor.visitBooleanAtomic(self)
            else:
                return visitor.visitChildren(self)




    def booleanAtomic(self):

        localctx = PowerEventDSLParser.BooleanAtomicContext(self, self._ctx, self.state)
        self.enterRule(localctx, 150, self.RULE_booleanAtomic)
        try:
            self.state = 681
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [2, 107, 108, 109, 111, 112, 118, 121]:
                self.enterOuterAlt(localctx, 1)
                self.state = 679
                self.comparisonExpr()
                pass
            elif token in [105, 106]:
                self.enterOuterAlt(localctx, 2)
                self.state = 680
                self.booleanLiteral()
                pass
            else:
                raise NoViableAltException(self)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ComparisonExprContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def arithmeticExpr(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(PowerEventDSLParser.ArithmeticExprContext)
            else:
                return self.getTypedRuleContext(PowerEventDSLParser.ArithmeticExprContext,i)


        def comparison(self):
            return self.getTypedRuleContext(PowerEventDSLParser.ComparisonContext,0)


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_comparisonExpr

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterComparisonExpr" ):
                listener.enterComparisonExpr(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitComparisonExpr" ):
                listener.exitComparisonExpr(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitComparisonExpr" ):
                return visitor.visitComparisonExpr(self)
            else:
                return visitor.visitChildren(self)




    def comparisonExpr(self):

        localctx = PowerEventDSLParser.ComparisonExprContext(self, self._ctx, self.state)
        self.enterRule(localctx, 152, self.RULE_comparisonExpr)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 683
            self.arithmeticExpr()
            self.state = 684
            self.comparison()
            self.state = 685
            self.arithmeticExpr()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ArithmeticExprContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def term(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(PowerEventDSLParser.TermContext)
            else:
                return self.getTypedRuleContext(PowerEventDSLParser.TermContext,i)


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_arithmeticExpr

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterArithmeticExpr" ):
                listener.enterArithmeticExpr(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitArithmeticExpr" ):
                listener.exitArithmeticExpr(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitArithmeticExpr" ):
                return visitor.visitArithmeticExpr(self)
            else:
                return visitor.visitChildren(self)




    def arithmeticExpr(self):

        localctx = PowerEventDSLParser.ArithmeticExprContext(self, self._ctx, self.state)
        self.enterRule(localctx, 154, self.RULE_arithmeticExpr)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 687
            self.term()
            self.state = 692
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==79 or _la==80:
                self.state = 688
                _la = self._input.LA(1)
                if not(_la==79 or _la==80):
                    self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 689
                self.term()
                self.state = 694
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class TermContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def factor(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(PowerEventDSLParser.FactorContext)
            else:
                return self.getTypedRuleContext(PowerEventDSLParser.FactorContext,i)


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_term

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterTerm" ):
                listener.enterTerm(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitTerm" ):
                listener.exitTerm(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitTerm" ):
                return visitor.visitTerm(self)
            else:
                return visitor.visitChildren(self)




    def term(self):

        localctx = PowerEventDSLParser.TermContext(self, self._ctx, self.state)
        self.enterRule(localctx, 156, self.RULE_term)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 695
            self.factor()
            self.state = 700
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==97 or _la==98:
                self.state = 696
                _la = self._input.LA(1)
                if not(_la==97 or _la==98):
                    self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 697
                self.factor()
                self.state = 702
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class FactorContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def numberWithUnit(self):
            return self.getTypedRuleContext(PowerEventDSLParser.NumberWithUnitContext,0)


        def variable(self):
            return self.getTypedRuleContext(PowerEventDSLParser.VariableContext,0)


        def arithmeticExpr(self):
            return self.getTypedRuleContext(PowerEventDSLParser.ArithmeticExprContext,0)


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_factor

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterFactor" ):
                listener.enterFactor(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitFactor" ):
                listener.exitFactor(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitFactor" ):
                return visitor.visitFactor(self)
            else:
                return visitor.visitChildren(self)




    def factor(self):

        localctx = PowerEventDSLParser.FactorContext(self, self._ctx, self.state)
        self.enterRule(localctx, 158, self.RULE_factor)
        try:
            self.state = 709
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [118, 121]:
                self.enterOuterAlt(localctx, 1)
                self.state = 703
                self.numberWithUnit()
                pass
            elif token in [107, 108, 109, 111, 112]:
                self.enterOuterAlt(localctx, 2)
                self.state = 704
                self.variable()
                pass
            elif token in [2]:
                self.enterOuterAlt(localctx, 3)
                self.state = 705
                self.match(PowerEventDSLParser.T__1)
                self.state = 706
                self.arithmeticExpr()
                self.state = 707
                self.match(PowerEventDSLParser.T__2)
                pass
            else:
                raise NoViableAltException(self)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class NumberWithUnitContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def numericAtom(self):
            return self.getTypedRuleContext(PowerEventDSLParser.NumericAtomContext,0)


        def unit(self):
            return self.getTypedRuleContext(PowerEventDSLParser.UnitContext,0)


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_numberWithUnit

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterNumberWithUnit" ):
                listener.enterNumberWithUnit(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitNumberWithUnit" ):
                listener.exitNumberWithUnit(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitNumberWithUnit" ):
                return visitor.visitNumberWithUnit(self)
            else:
                return visitor.visitChildren(self)




    def numberWithUnit(self):

        localctx = PowerEventDSLParser.NumberWithUnitContext(self, self._ctx, self.state)
        self.enterRule(localctx, 160, self.RULE_numberWithUnit)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 711
            self.numericAtom()
            self.state = 713
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if ((((_la - 113)) & ~0x3f) == 0 and ((1 << (_la - 113)) & 31) != 0):
                self.state = 712
                self.unit()


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ComparisonContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_comparison

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterComparison" ):
                listener.enterComparison(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitComparison" ):
                listener.exitComparison(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitComparison" ):
                return visitor.visitComparison(self)
            else:
                return visitor.visitChildren(self)




    def comparison(self):

        localctx = PowerEventDSLParser.ComparisonContext(self, self._ctx, self.state)
        self.enterRule(localctx, 162, self.RULE_comparison)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 715
            _la = self._input.LA(1)
            if not(((((_la - 99)) & ~0x3f) == 0 and ((1 << (_la - 99)) & 63) != 0)):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class BooleanLiteralContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_booleanLiteral

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterBooleanLiteral" ):
                listener.enterBooleanLiteral(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitBooleanLiteral" ):
                listener.exitBooleanLiteral(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitBooleanLiteral" ):
                return visitor.visitBooleanLiteral(self)
            else:
                return visitor.visitChildren(self)




    def booleanLiteral(self):

        localctx = PowerEventDSLParser.BooleanLiteralContext(self, self._ctx, self.state)
        self.enterRule(localctx, 164, self.RULE_booleanLiteral)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 717
            _la = self._input.LA(1)
            if not(_la==105 or _la==106):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class VariableContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def stringAtom(self):
            return self.getTypedRuleContext(PowerEventDSLParser.StringAtomContext,0)


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_variable

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterVariable" ):
                listener.enterVariable(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitVariable" ):
                listener.exitVariable(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitVariable" ):
                return visitor.visitVariable(self)
            else:
                return visitor.visitChildren(self)




    def variable(self):

        localctx = PowerEventDSLParser.VariableContext(self, self._ctx, self.state)
        self.enterRule(localctx, 166, self.RULE_variable)
        try:
            self.state = 740
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [107]:
                self.enterOuterAlt(localctx, 1)
                self.state = 719
                self.match(PowerEventDSLParser.T__106)
                self.state = 720
                self.match(PowerEventDSLParser.T__13)
                self.state = 721
                self.match(PowerEventDSLParser.T__60)
                self.state = 722
                self.stringAtom()
                pass
            elif token in [108]:
                self.enterOuterAlt(localctx, 2)
                self.state = 723
                self.match(PowerEventDSLParser.T__107)
                self.state = 724
                self.match(PowerEventDSLParser.T__13)
                self.state = 725
                self.match(PowerEventDSLParser.T__60)
                self.state = 726
                self.stringAtom()
                pass
            elif token in [109]:
                self.enterOuterAlt(localctx, 3)
                self.state = 727
                self.match(PowerEventDSLParser.T__108)
                self.state = 728
                self.match(PowerEventDSLParser.T__109)
                self.state = 729
                self.match(PowerEventDSLParser.T__81)
                self.state = 730
                self.match(PowerEventDSLParser.T__25)
                self.state = 731
                self.stringAtom()
                pass
            elif token in [111]:
                self.enterOuterAlt(localctx, 4)
                self.state = 732
                self.match(PowerEventDSLParser.T__110)
                self.state = 733
                self.match(PowerEventDSLParser.T__81)
                self.state = 734
                self.match(PowerEventDSLParser.T__25)
                self.state = 735
                self.stringAtom()
                pass
            elif token in [112]:
                self.enterOuterAlt(localctx, 5)
                self.state = 736
                self.match(PowerEventDSLParser.T__111)
                self.state = 737
                self.match(PowerEventDSLParser.T__81)
                self.state = 738
                self.match(PowerEventDSLParser.T__25)
                self.state = 739
                self.stringAtom()
                pass
            else:
                raise NoViableAltException(self)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class UnitContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser


        def getRuleIndex(self):
            return PowerEventDSLParser.RULE_unit

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterUnit" ):
                listener.enterUnit(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitUnit" ):
                listener.exitUnit(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitUnit" ):
                return visitor.visitUnit(self)
            else:
                return visitor.visitChildren(self)




    def unit(self):

        localctx = PowerEventDSLParser.UnitContext(self, self._ctx, self.state)
        self.enterRule(localctx, 168, self.RULE_unit)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 742
            _la = self._input.LA(1)
            if not(((((_la - 113)) & ~0x3f) == 0 and ((1 << (_la - 113)) & 31) != 0)):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx





