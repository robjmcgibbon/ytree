"""
YTreeArbor class and member functions



"""

#-----------------------------------------------------------------------------
# Copyright (c) ytree development team. All rights reserved.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

import h5py
import json
import numpy as np

from unyt.unit_registry import \
    UnitRegistry

from ytree.data_structures.arbor import \
    Arbor
from ytree.frontends.ytree.io import \
    YTreeDataFile, \
    YTreeRootFieldIO, \
    YTreeTreeFieldIO
from ytree.utilities.io import \
    _hdf5_yt_attr, \
    parse_h5_attr

class YTreeArbor(Arbor):
    """
    Class for Arbors created from the
    :func:`~ytree.data_structures.arbor.Arbor.save_arbor`
    or :func:`~ytree.data_structures.tree_node.TreeNode.save_tree` functions.
    """
    _root_field_io_class = YTreeRootFieldIO
    _tree_field_io_class = YTreeTreeFieldIO
    _suffix = ".h5"
    _node_io_attrs = ('_ai',)

    def _node_io_loop_prepare(self, nodes):
        if nodes is None:
            nodes = np.arange(self.size)
            ai = self._node_info['_ai']
        elif nodes.dtype == np.object:
            ai = np.array(
                [node._ai if node.is_root else node.root._ai
                 for node in nodes])
        else: # assume an array of indices
            ai = self._node_info['_ai'][nodes]

        # the order they will be processed
        io_order = np.argsort(ai)
        ai = ai[io_order]
        # array to return them to original order
        return_order = np.empty_like(io_order)
        return_order[io_order] = np.arange(io_order.size)

        dfi = np.digitize(ai, self._node_io._ei)
        udfi = np.unique(dfi)
        data_files = [self._node_io.data_files[i] for i in udfi]
        index_list = [io_order[dfi == i] for i in udfi]

        return data_files, index_list, return_order

    def _node_io_loop_start(self, data_file):
        data_file._field_cache = {}
        data_file.open()

    def _node_io_loop_finish(self, data_file):
        data_file._field_cache = {}
        data_file.close()

    def _parse_parameter_file(self):
        self._prefix = \
          self.filename[:self.filename.rfind(self._suffix)]
        fh = h5py.File(self.filename, "r")
        for attr in ["hubble_constant",
                     "omega_matter",
                     "omega_lambda"]:
            setattr(self, attr, fh.attrs[attr])
        if "unit_registry_json" in fh.attrs:
            self.unit_registry = \
              UnitRegistry.from_json(
                  parse_h5_attr(fh, "unit_registry_json"))
        self.box_size = _hdf5_yt_attr(
            fh, "box_size", unit_registry=self.unit_registry)
        self.field_info.update(
            json.loads(parse_h5_attr(fh, "field_info")))
        self.field_list = list(self.field_info.keys())
        self._size = fh.attrs["total_trees"]
        fh.close()

    def _plant_trees(self):
        if self.is_planted:
            return

        fh = h5py.File(self.filename, "r")
        self._node_info['uid'][:] = fh["data"]["uid"][()].astype(np.int64)
        self._node_io._si = fh["index"]["tree_start_index"][()]
        self._node_io._ei = fh["index"]["tree_end_index"][()]
        fh.close()

        self._node_info['_ai'][:] = np.arange(self.size)
        self._node_io.data_files = \
          [YTreeDataFile("%s_%04d%s" % (self._prefix, i, self._suffix))
           for i in range(self._node_io._si.size)]

    @classmethod
    def _is_valid(self, *args, **kwargs):
        """
        File should end in .h5, be loadable as an hdf5 file,
        and have "arbor_type" attribute.
        """
        fn = args[0]
        if not fn.endswith(self._suffix):
            return False
        try:
            with h5py.File(fn, "r") as f:
                if "arbor_type" not in f.attrs:
                    return False
                atype = f.attrs["arbor_type"]
                if hasattr(atype, "astype"):
                    atype = atype.astype(str)
                if atype != "YTreeArbor":
                    return False
        except BaseException:
            return False
        return True
