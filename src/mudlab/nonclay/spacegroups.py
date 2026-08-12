"""Space-group data for building references from a BGMN ``.str``.

A ``.str`` gives a space-group NUMBER + Wyckoff letters, not explicit symmetry
operations, so we need (a) the general-position operations per space group and
(b) the representative of each SPECIAL Wyckoff position (general positions list
all three coordinates, so they need no table). Both are the STANDARD ITA setting
and are VERIFIED against a COD CIF for each mineral added. Extend the tables as
more minerals are needed; a ``.str`` whose space group / special Wyckoff position
is not here is rejected with a clear message (the CIF path handles anything with
explicit ops).
"""

# General-position operations (x,y,z expression strings), standard ITA setting.
SG_OPS = {
    # Quartz enantiomorphs (verified vs COD 1011172 / 5000035, 9013321).
    152: ["x,y,z", "-y,x-y,1/3+z", "y-x,-x,2/3+z",
          "y,x,-z", "-x,y-x,1/3-z", "x-y,-y,2/3-z"],   # P3_1 2 1
    154: ["x,y,z", "-y,x-y,2/3+z", "y-x,-x,1/3+z",
          "y,x,-z", "x-y,-y,1/3-z", "-x,y-x,2/3-z"],   # P3_2 2 1
}

# Representatives of SPECIAL Wyckoff positions, keyed by (SG number, letter).
# (General positions are recognised by all three coordinates being present in the
# .str, so they are handled without a table entry.)
WYCKOFF = {
    (152, "a"): "x,0,1/3",   # quartz Si (3a)
    (154, "a"): "x,0,2/3",   # quartz Si (3a)
}
