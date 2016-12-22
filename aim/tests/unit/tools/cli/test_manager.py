# Copyright (c) 2016 Cisco Systems
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import ast

from aim import aim_manager
from aim.api import resource
from aim.tests.unit import test_aim_manager
from aim.tests.unit.tools.cli import test_shell as base
from aim.tools.cli.commands import manager as climanager


class TestManager(base.TestShell):

    def setUp(self):
        super(TestManager, self).setUp()
        self.mgr = aim_manager.AimManager()

    def test_load_domains(self):
        # create a VMM and PhysDom first
        pre_phys = resource.PhysicalDomain(name='pre-phys')
        pre_vmm = resource.PhysicalDomain(type='OpenStack', name='pre-vmm')
        ap = resource.ApplicationProfile(tenant_name='tn1', name='ap')
        pre_epg1 = resource.EndpointGroup(
            tenant_name='tn1', app_profile_name='ap', name='epg1')
        pre_epg2 = resource.EndpointGroup(
            tenant_name='tn1', app_profile_name='ap', name='epg2')
        self.mgr.create(self.ctx, resource.Tenant(name='tn1'))
        self.mgr.create(self.ctx, ap)
        self.mgr.create(self.ctx, pre_phys)
        self.mgr.create(self.ctx, pre_vmm)
        self.mgr.create(self.ctx, pre_epg2)
        self.mgr.create(self.ctx, pre_epg1)
        self.run_command('manager load-domains')
        # Verify pre-existing domains are still there
        self.assertIsNotNone(self.mgr.get(self.ctx, pre_phys))
        self.assertIsNotNone(self.mgr.get(self.ctx, pre_vmm))
        # Also the Domains defined in the config files exist
        self.assertIsNotNone(
            self.mgr.get(self.ctx, resource.PhysicalDomain(name='phys')))
        self.assertIsNotNone(
            self.mgr.get(self.ctx, resource.PhysicalDomain(name='phys2')))
        self.assertIsNotNone(
            self.mgr.get(self.ctx, resource.VMMDomain(type='OpenStack',
                                                      name='ostack')))
        self.assertIsNotNone(
            self.mgr.get(self.ctx, resource.VMMDomain(type='OpenStack',
                                                      name='ostack2')))
        # EPGs are still empty
        pre_epg1 = self.mgr.get(self.ctx, pre_epg1)
        pre_epg2 = self.mgr.get(self.ctx, pre_epg2)

        self.assertEqual([], pre_epg1.openstack_vmm_domain_names)
        self.assertEqual([], pre_epg1.physical_domain_names)
        self.assertEqual([], pre_epg2.openstack_vmm_domain_names)
        self.assertEqual([], pre_epg2.physical_domain_names)

        # Delete one of them, and use the replace flag
        self.mgr.delete(self.ctx, resource.VMMDomain(type='OpenStack',
                                                     name='ostack2'))
        self.run_command('manager load-domains --replace')

        # Now only 2 Domains each exist
        self.assertEqual(2, len(self.mgr.find(self.ctx, resource.VMMDomain)))
        self.assertEqual(2, len(self.mgr.find(self.ctx,
                                              resource.PhysicalDomain)))

        # EPGs are still empty
        pre_epg1 = self.mgr.get(self.ctx, pre_epg1)
        pre_epg2 = self.mgr.get(self.ctx, pre_epg2)

        self.assertEqual([], pre_epg1.openstack_vmm_domain_names)
        self.assertEqual([], pre_epg1.physical_domain_names)
        self.assertEqual([], pre_epg2.openstack_vmm_domain_names)
        self.assertEqual([], pre_epg2.physical_domain_names)

        # now update the current environment
        self.run_command('manager load-domains --replace --enforce')
        pre_epg1 = self.mgr.get(self.ctx, pre_epg1)
        pre_epg2 = self.mgr.get(self.ctx, pre_epg2)

        self.assertEqual(set(['ostack', 'ostack2']),
                         set(pre_epg1.openstack_vmm_domain_names))
        self.assertEqual(set(['phys', 'phys2']),
                         set(pre_epg1.physical_domain_names))
        self.assertEqual(set(['ostack', 'ostack2']),
                         set(pre_epg2.openstack_vmm_domain_names))
        self.assertEqual(set(['phys2', 'phys']),
                         set(pre_epg2.physical_domain_names))


class TestManagerResourceOpsBase(object):
    test_default_values = {}
    test_dn = None
    prereq_objects = None

    def setUp(self):
        super(TestManagerResourceOpsBase, self).setUp()
        self._mgr = aim_manager.AimManager()
        self._mgr._update_listeners = []

    def _run_manager_command(self, res_command, command, attributes,
                             klass=None):
        klass = klass or self.resource_class

        def transform_list(k, li):
            if k == 'static_paths':
                return "'%s'" % ' '.join(
                    [','.join(x) for x in
                     [['%s=%s' % (key, v) for key, v in y.iteritems()]
                      for y in li]])
            elif isinstance(li, list):
                return ','.join(li) if li else "''"
            return li if li not in ['', None] else "''"
        identity = [attributes[k] for k in
                    klass.identity_attributes]
        other = ['--%s %s' % (k, transform_list(k, v))
                 for k, v in attributes.iteritems()
                 if k not in klass.identity_attributes]
        return self.run_command(
            'manager ' + res_command + '-%s ' % command + ' '.join(
                identity + other) + ' -p')

    def _parse(self, res, klass=None):
        if not res.output_bytes:
            return None
        res = [' '.join(x.split()) for x in res.output_bytes.split('\n')][1:]
        res = [[x[:x.find(' ')], x[x.find(' ') + 1:]] for x in res if x]
        if ['Property', 'Value'] in res:
            # Remove additional tables
            # TODO(ivar): test expected faults
            res = res[:res.index(['Property', 'Value'])]
        res_dict = {}
        klass = klass or self.resource_class
        klass_attributes = klass.attributes
        for item in res:
            if len(item) == 2 and item[0] in klass_attributes():
                try:
                    # Try to load lists
                    loaded = ast.literal_eval(item[1])
                    if isinstance(loaded, list):
                        res_dict[item[0]] = loaded
                        continue
                except (SyntaxError, ValueError):
                    pass
                res_dict[item[0]] = item[1]
        return klass(**res_dict)

    def create(self, res_command, attributes, klass=None):
        res = self._run_manager_command(res_command, 'create', attributes,
                                        klass=klass)
        return self._parse(res, klass=klass)

    def delete(self, res_command, attributes):
        return self._run_manager_command(res_command, 'delete', attributes)

    def update(self, res_command, attributes):
        res = self._run_manager_command(res_command, 'update', attributes)
        return self._parse(res)

    def find(self, res_command, attributes):
        return self._run_manager_command(res_command, 'find', attributes)

    def get(self, res_command, attributes):
        res = self._run_manager_command(res_command, 'get', attributes)
        return self._parse(res)

    def describe(self, res_command):
        return self._run_manager_command(res_command, 'describe', {})

    def _test_resource_ops(self, resource, test_identity_attributes,
                           test_required_attributes, test_search_attributes,
                           test_update_attributes,
                           test_default_values,
                           test_dn, res_command):
        """Test basic operations for resources

        :param resource: resource type, eg: BridgeDomain
        :param test_identity_attributes: dictionary with test identity values
        eg: {'tenant_rn': 'foo', 'rn': 'bar'}
        :param test_required_attributes: dictionary with attributes required
        by the DB for successful object creation.
        :param test_search_attributes: dictionary with test search attributes,
        needs to be one/more of the resource's other_attributes suitable for
        search. eg: {'vrf_rn': 'shared'}
        :param test_update_attributes: some attributes already present in
        one of the previously specified ones that hold a different value.
        :param test_default_values: dictionary of default values to verify
        after object has been created
        :param test_dn: expected DN of created resource, if any.
        :return:
        """
        # Run the following only if ID attributes are also required
        if not (set(test_identity_attributes.keys()) -
                set(test_required_attributes.keys())):
            self.run_command('manager ' + res_command + '-create', raises=True)
            self.run_command('manager ' + res_command + '-update', raises=True)
            self.run_command('manager ' + res_command + '-delete', raises=True)
            self.run_command('manager ' + res_command + '-get', raises=True)

        creation_attributes = {}
        creation_attributes.update(test_required_attributes),
        creation_attributes.update(test_identity_attributes)

        # Verify successful creation
        r1 = self.create(res_command, creation_attributes)
        for k, v in creation_attributes.iteritems():
            self.assertEqual(v, test_aim_manager.getattr_canonical(r1, k))

        # Verify get
        r1 = self.get(res_command, test_identity_attributes)
        for k, v in creation_attributes.iteritems():
            self.assertEqual(v, test_aim_manager.getattr_canonical(r1, k))

        # Test update
        updates = {}
        updates.update(test_identity_attributes)
        updates.update(test_update_attributes)
        r1 = self.update(res_command, updates)
        for k, v in test_update_attributes.iteritems():
            self.assertEqual(v, test_aim_manager.getattr_canonical(r1, k))

        # Test delete
        self.delete(res_command, test_identity_attributes)
        self.assertIsNone(self.get(res_command, test_identity_attributes))

    def _create_prerequisite_objects(self):
        for obj in (self.prereq_objects or []):
            self.create(climanager.convert(type(obj).__name__), obj.__dict__,
                        klass=type(obj))

    def test_lifecycle(self):
        self._create_prerequisite_objects()
        self._test_resource_ops(
            self.resource_class,
            self.test_identity_attributes,
            self.test_required_attributes,
            self.test_search_attributes,
            self.test_update_attributes,
            self.test_default_values,
            self.test_dn, self.res_command)


class TestBridgeDomain(test_aim_manager.TestBridgeDomainMixin,
                       TestManagerResourceOpsBase, base.TestShell):
    pass


class TestSubnet(test_aim_manager.TestSubnetMixin, TestManagerResourceOpsBase,
                 base.TestShell):
    pass


class TestVRF(test_aim_manager.TestVRFMixin, TestManagerResourceOpsBase,
              base.TestShell):
    pass


class TestApplicationProfile(test_aim_manager.TestApplicationProfileMixin,
                             TestManagerResourceOpsBase,
                             base.TestShell):
    pass


class TestEndpointGroup(test_aim_manager.TestEndpointGroupMixin,
                        TestManagerResourceOpsBase,
                        base.TestShell):
    pass


class TestFilter(test_aim_manager.TestFilterMixin, TestManagerResourceOpsBase,
                 base.TestShell):
    pass


class TestFilterEntry(test_aim_manager.TestFilterEntryMixin,
                      TestManagerResourceOpsBase,
                      base.TestShell):
    pass


class TestContract(test_aim_manager.TestContractMixin,
                   TestManagerResourceOpsBase,
                   base.TestShell):
    pass


class TestContractSubject(test_aim_manager.TestContractSubjectMixin,
                          TestManagerResourceOpsBase,
                          base.TestShell):
    pass


class TestEndpoint(test_aim_manager.TestEndpointMixin,
                   TestManagerResourceOpsBase,
                   base.TestShell):
    pass


class TestVMMDomain(test_aim_manager.TestVMMDomainMixin,
                    TestManagerResourceOpsBase,
                    base.TestShell):
    pass


class TestPhysicalDomain(test_aim_manager.TestPhysicalDomainMixin,
                         TestManagerResourceOpsBase,
                         base.TestShell):
    pass


class TestL3Outside(test_aim_manager.TestL3OutsideMixin,
                    TestManagerResourceOpsBase,
                    base.TestShell):
    pass


class TestExternalNetwork(test_aim_manager.TestExternalNetworkMixin,
                          TestManagerResourceOpsBase,
                          base.TestShell):
    pass


class TestExternalSubnet(test_aim_manager.TestExternalSubnetMixin,
                         TestManagerResourceOpsBase,
                         base.TestShell):
    pass


class TestHostLink(test_aim_manager.TestHostLinkMixin,
                   TestManagerResourceOpsBase, base.TestShell):
    pass
