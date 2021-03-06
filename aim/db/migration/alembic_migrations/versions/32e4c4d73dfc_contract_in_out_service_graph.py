# Copyright (c) 2017 Cisco Systems
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

"""Add columns for in/out service-graphs in contract subject

Revision ID: 32e4c4d73dfc
Revises: ab95bd6852e8
Create Date: 2017-04-12 17:49:16.128172

"""

# revision identifiers, used by Alembic.
revision = '32e4c4d73dfc'
down_revision = 'ab95bd6852e8'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('aim_contract_subjects',
                  sa.Column('in_service_graph_name', sa.String(64),
                            server_default=''))
    op.add_column('aim_contract_subjects',
                  sa.Column('out_service_graph_name', sa.String(64),
                            server_default=''))


def downgrade():
    pass
