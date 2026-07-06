"""Pattern and project file parsers.

Currently: plain-text XY patterns. The old app's vendor formats (Philips
RD/UDF, Bruker RAW, CPI, ...) are ported later from
mudlab/file_parsers/xrd_parsers.
"""

from mudlab.file_parsers.xy_parser import parse_xy

__all__ = ["parse_xy"]
