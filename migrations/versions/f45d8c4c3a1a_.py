"""empty message

Revision ID: f45d8c4c3a1a
Revises: 
Create Date: 2018-04-22 10:59:53.213829

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f45d8c4c3a1a'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('user_agents',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_agent', sa.Text(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_agent')
    )
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('username', sa.String(length=32), nullable=False),
    sa.Column('passhash', sa.String(length=128), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('inviter_id', sa.Integer(), nullable=True),
    sa.Column('invites', sa.Integer(), server_default='0', nullable=False),
    sa.ForeignKeyConstraint(['inviter_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('username')
    )
    op.create_table('api_keys',
    sa.Column('hash', sa.String(length=10), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('keyhashsalt', sa.String(length=128), nullable=True),
    sa.Column('last_used', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('ip', sa.String(length=39), server_default='0.0.0.0', nullable=False),
    sa.Column('user_agent_id', sa.Integer(), nullable=True),
    sa.Column('csrf_token', sa.String(length=24), nullable=False),
    sa.Column('active', sa.Boolean(), server_default='t', nullable=False),
    sa.ForeignKeyConstraint(['user_agent_id'], ['user_agents.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('hash')
    )
    op.create_table('invites',
    sa.Column('code', sa.String(length=24), nullable=False),
    sa.Column('inviter_id', sa.Integer(), nullable=False),
    sa.Column('invitee_id', sa.Integer(), nullable=True),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('time_sent', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('from_ip', sa.String(length=39), server_default='0.0.0.0', nullable=False),
    sa.Column('active', sa.Boolean(), server_default='t', nullable=False),
    sa.ForeignKeyConstraint(['invitee_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['inviter_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('code')
    )
    op.create_table('permissions',
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('permission', sa.String(length=32), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('user_id', 'permission')
    )
    op.create_table('sessions',
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('hash', sa.String(length=10), nullable=False),
    sa.Column('last_used', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('ip', sa.String(length=39), server_default='0.0.0.0', nullable=False),
    sa.Column('user_agent_id', sa.Integer(), nullable=True),
    sa.Column('csrf_token', sa.String(length=24), nullable=False),
    sa.Column('active', sa.Boolean(), server_default='t', nullable=False),
    sa.ForeignKeyConstraint(['user_agent_id'], ['user_agents.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('user_id', 'hash')
    )
    op.create_table('api_permissions',
    sa.Column('api_key_hash', sa.String(length=10), nullable=False),
    sa.Column('permission', sa.String(length=32), nullable=False),
    sa.ForeignKeyConstraint(['api_key_hash'], ['api_keys.hash'], ),
    sa.PrimaryKeyConstraint('api_key_hash', 'permission')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('api_permissions')
    op.drop_table('sessions')
    op.drop_table('permissions')
    op.drop_table('invites')
    op.drop_table('api_keys')
    op.drop_table('users')
    op.drop_table('user_agents')
    # ### end Alembic commands ###
