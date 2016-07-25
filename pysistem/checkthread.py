# -*- coding: utf-8 -*-

import threading
from time import sleep

from pysistem import app, db
from pysistem.submissions.model import Submission
from pysistem.submissions.model import SubmissionLog
from pysistem.compilers.model import Compiler
from pysistem.submissions.const import STATUS_CWAIT, STATUS_WAIT, STATUS_CHECKING

CHECK_THREAD_TIME = app.config.get('CHECK_THREAD_TIME', 1)

Session = db.scoped_session(db.sessionmaker(bind=db.engine))


def check_thread_wake():
    """Check submissions"""
    session = Session()
    for sub in session.query(Submission).filter(
        Submission.status.in_([STATUS_CWAIT, STATUS_WAIT, STATUS_CHECKING])):

        compiler = session.query(Compiler).filter(Compiler.id == sub.compiler_id).first()
        if compiler and compiler.is_available():
            for log in session.query(SubmissionLog) \
                .filter(SubmissionLog.submission_id == sub.id):
                session.add(log)
                session.delete(log)
            if sub.compile()[0]:
                sub.check(session)
            session.commit()
    Session.remove()


def check_thread_main():
    """Start checking thread"""
    print('Starting checking thread')
    while True:
        check_thread_wake()
        sleep(CHECK_THREAD_TIME)


class CheckThread(threading.Thread):
    """Submission-checking thread"""
    def __init__(self, *args):
        threading.Thread.__init__(self, target=check_thread_main, args=args)
        self.daemon = True
