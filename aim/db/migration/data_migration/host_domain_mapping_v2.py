# Copyright (c) 2018 Cisco Systems
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

import sqlalchemy as sa


HostDomainMappingV2 = sa.Table(
    'aim_host_domain_mapping_v2', sa.MetaData(),
    sa.Column('host_name', sa.String(128)),
    sa.Column('domain_name', sa.String(64)),
    sa.Column('domain_type', sa.Enum('PhysDom', 'OpenStack', 'Kubernetes',
                                     'VMware'))
)

HostDomainMapping = sa.Table(
    'aim_host_domain_mapping', sa.MetaData(),
    sa.Column('host_name', sa.String(128)),
    sa.Column('vmm_domain_name', sa.String(64)),
    sa.Column('physical_domain_name', sa.String(64))
)


def migrate(session):
    with session.begin(subtransactions=True):
        migrations = []
        for mapping in session.query(HostDomainMapping).all():
            if mapping.vmm_domain_name:
                migrations.append({'host_name': mapping.host_name,
                                   'domain_name': mapping.vmm_domain_name,
                                   'domain_type': 'OpenStack'})
            if mapping.physical_domain_name:
                migrations.append({'host_name': mapping.host_name,
                                   'domain_name': mapping.physical_domain_name,
                                   'domain_type': 'PhysDom'})
        session.execute(HostDomainMapping.delete())
        if migrations:
            session.execute(HostDomainMappingV2.insert().values(migrations))
