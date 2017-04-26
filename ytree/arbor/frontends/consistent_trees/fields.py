"""
ConsistentTreesArbor fields



"""

#-----------------------------------------------------------------------------
# Copyright (c) 2017, Britton Smith <brittonsmith@gmail.com>
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

from ytree.arbor.fields import \
    FieldInfoContainer

p_unit = "unitary"
r_unit = "kpc"
v_unit = "km/s"

class ConsistentTreesFieldInfo(FieldInfoContainer):
    alias_fields = (
        ("scale_factor", "scale", None),
        ("mass", "Mvir", "Msun"),
        ("virial_mass", "Mvir", "Msun"),
        ("virial_radius", "Rvir", r_unit),
        ("scale_radius", "rs", r_unit),
        ("velocity_dispersion", "vrms", v_unit),
        ("position_x", "x", p_unit),
        ("position_y", "y", p_unit),
        ("position_z", "z", p_unit),
        ("velocity_x", "vx", v_unit),
        ("velocity_y", "vy", v_unit),
        ("velocity_z", "vz", v_unit),
        ("angular_momentum_x", "Jx", None),
        ("angular_momentum_y", "Jy", None),
        ("angular_momentum_z", "Jz", None),
        ("spin_parameter", "Spin", None),
    )
