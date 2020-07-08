"""
ConsistentTreesArbor class and member functions



"""

#-----------------------------------------------------------------------------
# Copyright (c) ytree development team. All rights reserved.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

import glob
import numpy as np
import operator
import os

from yt.funcs import \
    get_pbar

from ytree.data_structures.arbor import \
    Arbor
from ytree.data_structures.tree_node import \
    TreeNode

from ytree.frontends.consistent_trees.fields import \
    ConsistentTreesFieldInfo
from ytree.frontends.consistent_trees.io import \
    ConsistentTreesDataFile, \
    ConsistentTreesTreeFieldIO, \
    ConsistentTreesHlistDataFile
from ytree.frontends.consistent_trees.utilities import \
    parse_ctrees_header
from ytree.frontends.rockstar.arbor import \
    RockstarArbor

from ytree.utilities.exceptions import \
    ArborDataFileEmpty
from ytree.utilities.io import \
    f_text_block

class ConsistentTreesArbor(Arbor):
    """
    Arbors loaded from consistent-trees tree_*.dat files.
    """

    _field_info_class = ConsistentTreesFieldInfo
    _tree_field_io_class = ConsistentTreesTreeFieldIO
    _default_dtype = np.float32

    def _node_io_loop_prepare(self, root_nodes):
        return self.data_files, [root_nodes]

    def _node_io_loop_start(self, data_file):
        data_file.open()

    def _node_io_loop_finish(self, data_file):
        data_file.close()

    def _get_data_files(self):
        self.data_files = [ConsistentTreesDataFile(self.filename)]

    def _parse_parameter_file(self, filename=None,
                              lines_after_header=True):
        if filename is None:
            filename = self.filename
        fi = parse_ctrees_header(
            self, filename,
            lines_after_header=lines_after_header)
        self.field_list = list(fi.keys())
        self.field_info.update(fi)

    def _plant_trees(self):
        self._trees = np.empty(self._ntrees, dtype=np.object)
        if self._ntrees == 0:
            return

        lkey = len("tree ")+1
        block_size = 32768

        data_file = self.data_files[0]

        data_file.open()
        data_file.fh.seek(0, 2)
        file_size = data_file.fh.tell()
        pbar = get_pbar("Loading tree roots", file_size)
        data_file.fh.seek(self._hoffset)

        offset = self._hoffset
        itree = 0
        nblocks = np.ceil(float(file_size-self._hoffset) /
                          block_size).astype(np.int64)
        for ib in range(nblocks):
            my_block = min(block_size, file_size - offset)
            if my_block <= 0: break
            buff = data_file.fh.read(my_block)
            lihash = -1
            for ih in range(buff.count("#")):
                ihash = buff.find("#", lihash+1)
                inl = buff.find("\n", ihash+1)
                if inl < 0:
                    buff += data_file.fh.readline()
                    inl = len(buff)
                uid = int(buff[ihash+lkey:inl])
                lihash = ihash
                my_node = TreeNode(uid, arbor=self, root=True)
                my_node._si = offset + inl + 1
                my_node._fi = 0
                self._trees[itree] = my_node
                if itree > 0:
                    self._trees[itree-1]._ei = offset + ihash - 1
                itree += 1
            offset = data_file.fh.tell()
            pbar.update(offset)
        self._trees[-1]._ei = offset
        data_file.close()
        pbar.finish()

    @classmethod
    def _is_valid(self, *args, **kwargs):
        """
        File should end in .dat and have a line in the header
        with the string, "Consistent Trees".
        """
        fn = args[0]
        if not fn.endswith(".dat"): return False
        with open(fn, "r") as f:
            valid = False
            while True:
                line = f.readline()
                if line is None or not line.startswith("#"):
                    break
                if "Consistent Trees" in line:
                    valid = True
                    break
            if not valid: return False
        return True

class ConsistentTreesGroupArbor(ConsistentTreesArbor):
    """
    Arbors loaded from consistent-trees locations.dat files.
    """

    def _node_io_loop_prepare(self, root_nodes):
        fi = np.array([node._fi for node in root_nodes])
        ufi = np.unique(fi)
        data_files = [self.data_files[i] for i in ufi]
        node_list = [root_nodes[fi == i] for i in ufi]
        return data_files, node_list

    def _get_data_files(self):
        pass

    def _parse_parameter_file(self):
        f = open(self.filename, 'r')
        f.readline()
        self._hoffset = f.tell()
        line = f.readline()
        if not line:
            raise ArborDataFileEmpty(self.filename)

        fn = os.path.join(self.directory, line.split()[-1])
        super(ConsistentTreesGroupArbor, self)._parse_parameter_file(
            filename=fn, lines_after_header=False)

    def _plant_trees(self):
        f = open(self.filename, 'r')
        f.seek(self._hoffset)
        ldata = list(map(
            lambda x: [int(x[0]), int(x[1]), int(x[2]), x[3], len(x[0])],
            [line.split() for line, _ in f_text_block(f, pbar_string='Reading locations')]
            ))
        f.close()

        # It's faster to create and sort arrays and then sort ldata
        # for some reason.
        dfns = np.unique([datum[3] for datum in ldata])
        dfns.sort()
        fids = np.array([datum[1] for datum in ldata])
        fids.sort()
        ufids = np.unique(fids)
        ufids.sort()

        # Some data files may be empty and so unlisted.
        # Make sure file ids and names line up.
        data_files = [None]*(ufids.max()+1)
        for i,fid in enumerate(ufids):
            data_files[fid] = dfns[i]
        self.data_files = \
          [None if fn is None
           else ConsistentTreesDataFile(os.path.join(self.directory, fn))
           for fn in data_files]

        ldata.sort(key=operator.itemgetter(1, 2))
        ntrees = len(ldata)
        pbar = get_pbar("Loading tree roots", ntrees)
        self._trees = np.empty(ntrees, dtype=np.object)

        # Set end offsets for each tree.
        # We don't get them from the location file.
        lkey = len("tree ")+3 # length of the separation line between trees
        same_file = np.diff(fids, append=fids[-1]+1) == 0

        for i, tdata in enumerate(ldata):
            my_node        = TreeNode(tdata[0], arbor=self, root=True)
            my_node._si    = tdata[2]
            my_node._fi    = tdata[1]
            # Get end index from next tree.
            if same_file[i]:
                my_node._ei = ldata[i+1][2] - lkey - tdata[4]
            self._trees[i] = my_node
            pbar.update(i)
        pbar.finish()

        # Get end index for last trees in files.
        for i in np.where(~same_file)[0]:
            data_file = self.data_files[fids[i]]
            data_file.open()
            data_file.fh.seek(0, 2)
            self._trees[i]._ei = data_file.fh.tell()
            data_file.close()

    @classmethod
    def _is_valid(self, *args, **kwargs):
        """
        File should end in .dat and have a line in the header
        with the string, "Consistent Trees".
        """
        fn = args[0]
        if not os.path.basename(fn) == 'locations.dat':
            return False
        with open(fn, "r") as f:
            valid = False
            while True:
                line = f.readline()
                if line is None or not line.startswith("#"):
                    break
                if "TreeRootID FileID Offset Filename" in line:
                    valid = True
            if not valid:
                return False
        return True

class ConsistentTreesHlistArbor(RockstarArbor):
    """
    Class for Arbors created from consistent-trees hlist_*.list files.

    This is a hybrid type with multiple catalog files like the rockstar
    frontend, but with headers structured like consistent-trees.
    """

    _has_uids = True
    _field_info_class = ConsistentTreesFieldInfo
    _data_file_class = ConsistentTreesHlistDataFile

    def _parse_parameter_file(self):
        ConsistentTreesArbor._parse_parameter_file(
            self, lines_after_header=False)

    def _get_data_files(self):
        """
        Get all out_*.list files and sort them in reverse order.
        """
        prefix = os.path.join(os.path.dirname(self.filename), "hlist_")
        suffix = ".list"
        my_files = glob.glob("%s*%s" % (prefix, suffix))

        # sort by catalog number
        my_files.sort(
            key=lambda x:
            self._get_file_index(x, prefix, suffix),
            reverse=True)
        self.data_files = \
          [self._data_file_class(f, self) for f in my_files]

    def _get_file_index(self, f, prefix, suffix):
        return float(f[f.find(prefix)+len(prefix):f.rfind(suffix)])

    @classmethod
    def _is_valid(self, *args, **kwargs):
        """
        File should end in .list.
        """
        fn = args[0]
        if not os.path.basename(fn).startswith("hlist") or \
          not fn.endswith(".list"):
            return False
        return True
