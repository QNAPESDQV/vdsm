# Copyright 2015 Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301 USA
#
# Refer to the README and COPYING files for full details of the license
#

from contextlib import contextmanager

from testlib import VdsmTestCase, namedTemporaryDir
from storagefakelib import FakeLVM

from storage import blockSD
from storage import lvm as real_lvm


class FakeLVMSimpleVGTests(VdsmTestCase):
    VG_NAME = '1ffead52-7363-4968-a8c7-3bc34504d452'
    DEVICES = ['360014054d75cb132d474c0eae9825766']
    LV_NAME = '54e3378a-b2f6-46ff-b2da-a9c82522a55e'
    LV_SIZE_MB = 1024

    def validate_properties(self, props, obj):
        for var, val in props.items():
            self.assertEqual(val, getattr(obj, var))

    @contextmanager
    def base_config(self):
        """
        Create a simple volume group from a single 10G LUN.

        lvm.createVG('1ffead52-7363-4968-a8c7-3bc34504d452',
                     ['360014054d75cb132d474c0eae9825766'],
                     blockSD.STORAGE_UNREADY_DOMAIN_TAG,
                     blockSD.VG_METADATASIZE)

        print lvm.getVG('1ffead52-7363-4968-a8c7-3bc34504d452')
        VG(uuid='15hlPF-V3eG-F9Cp-SGtu-4Mq0-28Do-HC806y',
           name='1ffead52-7363-4968-a8c7-3bc34504d452',
           attr=VG_ATTR(permission='w', resizeable='z', exported='-',
                        partial='-', allocation='n', clustered='-'),
           size='10334765056', free='10334765056', extent_size='134217728',
           extent_count='77', free_count='77',
           tags=('RHAT_storage_domain_UNREADY',), vg_mda_size='134217728',
           vg_mda_free='67107328', lv_count='0', pv_count='1',
           pv_name=('/dev/mapper/360014054d75cb132d474c0eae9825766',),
           writeable=True, partial='OK')

        print lvm.getPV('360014054d75cb132d474c0eae9825766')
        PV(uuid='fIRjbD-usOA-tYgW-b2Uz-oUly-AJ49-bMMjYe',
           name='/dev/mapper/360014054d75cb132d474c0eae9825766',
           size='10334765056', vg_name='1ffead52-7363-4968-a8c7-3bc34504d452',
           vg_uuid='15hlPF-V3eG-F9Cp-SGtu-4Mq0-28Do-HC806y',
           pe_start='138412032', pe_count='77', pe_alloc_count='0',
           mda_count='2', dev_size='10737418240',
           guid='360014054d75cb132d474c0eae9825766')
        """
        with namedTemporaryDir() as tmpdir:
            lvm = FakeLVM(tmpdir)
            lvm.createVG(self.VG_NAME, self.DEVICES,
                         blockSD.STORAGE_UNREADY_DOMAIN_TAG,
                         blockSD.VG_METADATASIZE)
            yield lvm

    def test_vg_properties(self):
        expected = dict(
            name=self.VG_NAME,
            size='10334765056',
            free='10334765056',
            extent_size='134217728',
            extent_count='77',
            free_count='77',
            tags=(blockSD.STORAGE_UNREADY_DOMAIN_TAG,),
            vg_mda_size='134217728',
            lv_count='0',
            pv_count='1',
            writeable=True,
            partial='OK',
            pv_name=tuple(('/dev/mapper/%s' % d for d in self.DEVICES)))
        with self.base_config() as lvm:
            vg = lvm.getVG(self.VG_NAME)
            self.validate_properties(expected, vg)

    def test_vg_attributes(self):
        expected = real_lvm.VG_ATTR(permission='w', resizeable='z',
                                    exported='-', partial='-',
                                    allocation='n', clustered='-')
        with self.base_config() as lvm:
            vg = lvm.getVG(self.VG_NAME)
            self.assertEqual(expected, vg.attr)

    def test_vg_mda_free(self):
        # It is too complex to emulate vg_mda_free and at this point we do not
        # rely on this value.  For this reason, FakeLVM sets it to None.
        with self.base_config() as lvm:
            vg = lvm.getVG(self.VG_NAME)
            self.assertEqual(None, vg.vg_mda_free)

    def test_pv_properties(self):
        expected = dict(
            name='/dev/mapper/%s' % self.DEVICES[0],
            size='10334765056',
            vg_name=self.VG_NAME,
            pe_count='77',
            pe_alloc_count='0',
            mda_count='2',
            dev_size='10737418240',
            guid=self.DEVICES[0],
        )
        with self.base_config() as lvm:
            pv = lvm.getPV(self.DEVICES[0])
            self.validate_properties(expected, pv)

    def test_pv_vg_uuid(self):
        with self.base_config() as lvm:
            vg = lvm.getVG(self.VG_NAME)
            pv = lvm.getPV(self.DEVICES[0])
            self.assertEqual(pv.vg_uuid, vg.uuid)

    def test_pv_pe_start(self):
        # As documented in FakeLVM, pe_start is not emulated and should be None
        with self.base_config() as lvm:
            pv = lvm.getPV(self.DEVICES[0])
            self.assertIsNone(pv.pe_start)

    def test_lv_properties(self):
        """
        Create a single logical volume on the base configuration.

        lvm.createLV('1ffead52-7363-4968-a8c7-3bc34504d452',
                     '54e3378a-b2f6-46ff-b2da-a9c82522a55e', 1024)

        print lvm.getLV('1ffead52-7363-4968-a8c7-3bc34504d452',
                        '54e3378a-b2f6-46ff-b2da-a9c82522a55e')
        LV(uuid='89tSvh-HJl5-SO2K-O36t-3qkj-Zo2J-yugkjk',
           name='54e3378a-b2f6-46ff-b2da-a9c82522a55e',
           vg_name='1ffead52-7363-4968-a8c7-3bc34504d452',
           attr=LV_ATTR(voltype='-', permission='w', allocations='i',
                        fixedminor='-', state='a', devopen='-', target='-',
                        zero='-'),
           size='1073741824', seg_start_pe='0',
           devices='/dev/mapper/360014054d75cb132d474c0eae9825766(0)',
           tags=(), writeable=True, opened=False, active=True)
        """
        props = dict(
            name=self.LV_NAME,
            vg_name=self.VG_NAME,
            size='1073741824',
            seg_start_pe='0',
            tags=(),
            writeable=True,
            opened=False,
            active=True,
        )
        attrs = real_lvm.LV_ATTR(voltype='-', permission='w', allocations='i',
                                 fixedminor='-', state='a', devopen='-',
                                 target='-', zero='-')
        with self.base_config() as lvm:
            lvm.createLV(self.VG_NAME, self.LV_NAME, str(self.LV_SIZE_MB))
            lv = lvm.getLV(self.VG_NAME, self.LV_NAME)
            self.validate_properties(props, lv)
            self.assertEqual(attrs, lv.attr)

            # As documented in FakeLVM, devices is not emulated and is None
            self.assertIsNone(lv.devices)