"""
utilities



"""

#-----------------------------------------------------------------------------
# Copyright (c) 2016, Britton Smith <brittonsmith@gmail.com>
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

import numpy as np
import os
from yt.units.yt_array import \
    YTArray, \
    YTQuantity

def _hdf5_yt_attr(fh, attr, unit_registry=None):
    val = fh.attrs[attr]
    units = ""
    ufield = "%s_units" % attr
    if ufield in fh.attrs:
        units = fh.attrs[ufield]
    if units == "dimensionless":
        units = ""
    if units != "":
        if isinstance(val, np.ndarray):
            val = YTArray(val, units, registry=unit_registry)
        else:
            val = YTQuantity(val, units, registry=unit_registry)
    return val

def _hdf5_yt_array_lite(fh, field):
    units = ""
    if "units" in fh[field].attrs:
        units = fh[field].attrs["units"]
    if units == "dimensionless": units = ""
    return (fh[field].value, units)

def not_on_drone(func, *args, **kwargs):
    """
    Do not run the function if environment variable DRONE=1.
    """

    env = dict(os.environ)
    def myfunc():
        if int(env.get("DRONE", 0)) == 1:
            return
        return func(*args, **kwargs)
    return myfunc