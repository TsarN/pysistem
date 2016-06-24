# -*- coding: utf-8 -*-

import threading
from time import sleep

from pysistem import app, db
from pysistem.submissions.model import Submission
from pysistem.submissions.model import SubmissionLog
from pysistem.compilers.model import Compiler
from pysistem.submissions.const import STATUS_CWAIT, STATUS_WAIT

CHECK_THREAD_TIME = app.config.get('CHECK_THREAD_TIME', 1)

Session = db.scoped_session(db.sessionmaker(bind=db.engine))

def check_thread_wake():
    """Check submissions"""
    session = Session()
    for sub in session.query(Submission).filter( \
        Submission.status.in_([STATUS_CWAIT, STATUS_WAIT])):

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

check_thread_lock = threading.Lock()
alive = True

def check_thread_main():
    global alive
    if check_thread_lock.locked():
        print('Too late!')
    check_thread_lock.acquire()
    print('Starting checking thread')
    while check_thread_lock.locked() and alive:
        check_thread_wake()
        sleep(CHECK_THREAD_TIME)
    print('Checking thread exited')
    check_thread_lock.release()

class CheckThread(threading.Thread):
    def __init__(self, *args):
        threading.Thread.__init__(self, target=check_thread_main, args=args)
        self.daemon = True

    def is_locked(self):
        return check_thread_lock.locked()

    def unlock(self):
        global alive
        alive = False
        check_thread_lock.release()
