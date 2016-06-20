from sqlalchemy import *
from migrate import *


from migrate.changeset import schema
pre_meta = MetaData()
post_meta = MetaData()
auto_mark = Table('auto_mark', post_meta,
    Column('id', Integer, primary_key=True, nullable=False),
    Column('type', Integer),
    Column('required', Integer),
    Column('mark', String(length=4)),
    Column('points', Integer),
    Column('lesson_id', Integer),
)

checker = Table('checker', post_meta,
    Column('id', Integer, primary_key=True, nullable=False),
    Column('name', String(length=256)),
    Column('source', Text),
    Column('status', Integer),
    Column('compile_log', Text),
    Column('problem_id', Integer),
    Column('compiler_id', Integer),
)

compiler = Table('compiler', post_meta,
    Column('id', Integer, primary_key=True, nullable=False),
    Column('name', String(length=80)),
    Column('lang', String(length=80)),
    Column('cmd_compile', String(length=8192)),
    Column('cmd_run', String(length=8192)),
    Column('autodetect', String(length=16)),
    Column('executable', String(length=80)),
)

contest = Table('contest', post_meta,
    Column('id', Integer, primary_key=True, nullable=False),
    Column('name', String(length=80)),
    Column('rules', String(length=8)),
    Column('start', DateTime),
    Column('end', DateTime),
    Column('freeze', DateTime),
    Column('unfreeze_after_end', Boolean),
)

contest_problem_association = Table('contest_problem_association', post_meta,
    Column('contest_id', Integer, primary_key=True, nullable=False),
    Column('problem_id', Integer, primary_key=True, nullable=False),
    Column('prefix', String(length=8)),
)

group = Table('group', post_meta,
    Column('id', Integer, primary_key=True, nullable=False),
    Column('name', String(length=80)),
)

group_contest_association = Table('group_contest_association', post_meta,
    Column('group_id', Integer, primary_key=True, nullable=False),
    Column('contest_id', Integer, primary_key=True, nullable=False),
)

group_user_association = Table('group_user_association', post_meta,
    Column('group_id', Integer, primary_key=True, nullable=False),
    Column('user_id', Integer, primary_key=True, nullable=False),
    Column('role', String(length=8)),
)

lesson = Table('lesson', post_meta,
    Column('id', Integer, primary_key=True, nullable=False),
    Column('name', String(length=80)),
    Column('start', DateTime),
    Column('end', DateTime),
    Column('group_id', Integer),
    Column('contest_id', Integer),
)

lesson_user_association = Table('lesson_user_association', post_meta,
    Column('lesson_id', Integer, primary_key=True, nullable=False),
    Column('user_id', Integer, primary_key=True, nullable=False),
    Column('mark', String(length=4)),
    Column('points', Integer),
)

problem = Table('problem', post_meta,
    Column('id', Integer, primary_key=True, nullable=False),
    Column('name', String(length=80)),
    Column('description', String(length=256)),
    Column('statement', Text),
    Column('time_limit', Integer),
    Column('memory_limit', Integer),
)

setting = Table('setting', post_meta,
    Column('name', String(length=80), primary_key=True, nullable=False),
    Column('type', Integer),
    Column('value_int', Integer),
    Column('value_string', Text),
)

submission = Table('submission', post_meta,
    Column('id', Integer, primary_key=True, nullable=False),
    Column('source', Text),
    Column('status', Integer),
    Column('result', Integer),
    Column('compile_log', Text),
    Column('score', Integer),
    Column('submitted', DateTime),
    Column('user_id', Integer),
    Column('compiler_id', Integer),
    Column('problem_id', Integer),
    Column('current_test_id', Integer),
)

submission_log = Table('submission_log', post_meta,
    Column('result', Integer),
    Column('log', Text),
    Column('stdout', Text),
    Column('submission_id', Integer, primary_key=True, nullable=False),
    Column('test_pair_id', Integer, primary_key=True, nullable=False),
)

test_group = Table('test_group', post_meta,
    Column('id', Integer, primary_key=True, nullable=False),
    Column('score', Integer),
    Column('score_per_test', Integer),
    Column('check_all', Boolean),
    Column('problem_id', Integer),
)

test_pair = Table('test_pair', post_meta,
    Column('id', Integer, primary_key=True, nullable=False),
    Column('input', Text),
    Column('pattern', Text),
    Column('test_group_id', Integer),
)

user = Table('user', post_meta,
    Column('id', Integer, primary_key=True, nullable=False),
    Column('username', String(length=40)),
    Column('password', String(length=64)),
    Column('first_name', String(length=32)),
    Column('last_name', String(length=32)),
    Column('email', String(length=32)),
    Column('role', String(length=8)),
)


def upgrade(migrate_engine):
    # Upgrade operations go here. Don't create your own engine; bind
    # migrate_engine to your metadata
    pre_meta.bind = migrate_engine
    post_meta.bind = migrate_engine
    post_meta.tables['auto_mark'].create()
    post_meta.tables['checker'].create()
    post_meta.tables['compiler'].create()
    post_meta.tables['contest'].create()
    post_meta.tables['contest_problem_association'].create()
    post_meta.tables['group'].create()
    post_meta.tables['group_contest_association'].create()
    post_meta.tables['group_user_association'].create()
    post_meta.tables['lesson'].create()
    post_meta.tables['lesson_user_association'].create()
    post_meta.tables['problem'].create()
    post_meta.tables['setting'].create()
    post_meta.tables['submission'].create()
    post_meta.tables['submission_log'].create()
    post_meta.tables['test_group'].create()
    post_meta.tables['test_pair'].create()
    post_meta.tables['user'].create()


def downgrade(migrate_engine):
    # Operations to reverse the above upgrade go here.
    pre_meta.bind = migrate_engine
    post_meta.bind = migrate_engine
    post_meta.tables['auto_mark'].drop()
    post_meta.tables['checker'].drop()
    post_meta.tables['compiler'].drop()
    post_meta.tables['contest'].drop()
    post_meta.tables['contest_problem_association'].drop()
    post_meta.tables['group'].drop()
    post_meta.tables['group_contest_association'].drop()
    post_meta.tables['group_user_association'].drop()
    post_meta.tables['lesson'].drop()
    post_meta.tables['lesson_user_association'].drop()
    post_meta.tables['problem'].drop()
    post_meta.tables['setting'].drop()
    post_meta.tables['submission'].drop()
    post_meta.tables['submission_log'].drop()
    post_meta.tables['test_group'].drop()
    post_meta.tables['test_pair'].drop()
    post_meta.tables['user'].drop()
