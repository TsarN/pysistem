# -*- coding: utf-8 -*-
import subprocess
import tempfile
import hashlib
import os
import shlex

from pysistem import app, db

try:
    from pysistem.conf import COMPILE_TIME_LIMIT
except ImportError:
    from pysistem.conf_default import COMPILE_TIME_LIMIT

class Compiler(db.Model):
    """A submission runner backend

    Fields:
    id -- unique compiler identifier
    name -- compiler name
    lang -- extension of source files compiled by this compiler
    cmd_compile -- pattern for compilation command
    cmd_run -- pattern for execute command
    autodetect -- if this compiler is autodetected, unique autodetect identifier, else None
    executable -- executable name of compiler

    Relationships:
    submissions -- All submissions that were compiled by this compiler
    checkers -- All checkers that were compiled by this compiler
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80))
    lang = db.Column(db.String(80))
    cmd_compile = db.Column(db.String(8192))
    cmd_run = db.Column(db.String(8192))
    autodetect = db.Column(db.String(16))
    executable = db.Column(db.String(80))

    submissions = db.relationship('Submission', cascade="all,delete",
                                  backref='compiler', lazy="dynamic")
    checkers = db.relationship('Checker', cascade="all,delete",
                               backref='compiler', lazy="dynamic")

    def __init__(self, name=None, lang=None, cmd_compile=None, cmd_run=None):
        self.name = name
        self.lang = lang
        self.cmd_compile = cmd_compile
        self.cmd_run = cmd_run

    def __repr__(self):
        return '<Compiler %r>' % self.name

    def compile(self, src, exe):
        """Compile source file

        Arguments:
        src -- path to source file
        exe -- path to resulting executable

        Returns:
        Tuple: (Successfully compiled, compiler log)
        """
        cmd = self.cmd_compile.replace('%exe%', exe).replace('%src%', src)
        try:
            result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, timeout=COMPILE_TIME_LIMIT)
        except subprocess.TimeoutExpired:
            return (False, "[INVOKER] Compilation time limit (%d seconds) expired" % COMPILE_TIME_LIMIT);
        return (result.returncode == 0, result.stdout or '')

    def run(self, exe, src_path='', time_limit=1000, memory_limit=65536, stdin=''):
        """Run executable in sandbox

        Arguments:
        exe -- path to executable to run
        src_path -- path to source file, required for intepretable languages
        time_limit -- maximum execution time of program in milliseconds
        memory_limit -- maximum memory usage of program in KiB
        stdin -- stdin contents to pass to program

        Returns:
        Tuple: (Exit code: see runsbox(1), Program's stdout, Program's stderr: b'')
        """
        hasher = hashlib.new('md5')
        hasher.update(str.encode(exe))
        dig = hasher.hexdigest()
        input_path = tempfile.gettempdir() + '/pysistem_runner_input_%d%s' % (self.id, dig)

        with open(input_path, 'w') as input_file:
            input_file.write(stdin)

        output_path = tempfile.gettempdir() + '/pysistem_runner_output_%d%s' % (self.id, dig)

        cmd = shlex.split(self.cmd_run.replace('%exe%', exe).replace('%src%', src_path))
        cmd = ['runsbox', str(time_limit), str(memory_limit), input_path, output_path] + cmd

        if os.path.exists('/SANDBOX'): # pragma: no cover
            proc = subprocess.Popen(cmd, cwd='/SANDBOX')
        else:  # pragma: no cover
            proc = subprocess.Popen(cmd)
        proc.wait()
        stdout = b''
        with open(output_path, "rb") as output_file:
            stdout = output_file.read()

        os.remove(input_path)
        os.remove(output_path)
        return (proc.returncode, stdout, b'')

    def is_available(self):
        """Check if compiler is available on this machine"""
        from distutils.spawn import find_executable
        path = os.environ['PATH']
        if app.config.get('PATH_EXTRA'): # pragma: no cover
            path = path + os.pathsep + os.pathsep.join(app.config.get('PATH_EXTRA'))
        return bool(find_executable(self.executable, path=path))

detectable_compilers = {
    "gcc": {
        "name": "GNU C Compiler %s",
        "executable": "gcc",
        "lang": "c",
        "find_version": "%s --version | sed -n 's/^gcc (.*) //p'",
        "build": "__compiler__ -Wall --std=c11 -O2 __src__ -o __exe__"
    },
    "gxx": {
        "name": "GNU C++ Compiler %s",
        "executable": "g++",
        "lang": "cpp",
        "find_version": "%s --version | sed -n 's/^g++ (.*) //p'",
        "build": "__compiler__ -Wall --std=c++11 -O2 __src__ -o __exe__"
    },
    "fpc": {
        "name": "Free Pascal Compiler %s",
        "executable": "fpc",
        "lang": "pas",
        "find_version": "%s -iV",
        "build": """cd `dirname __src__`; mkdir -p __src___WORK &&
        __compiler__ -Mdelphi __src__ -FE__src___WORK &&
        cp __src___WORK/`basename __src__ .pas` __exe__;
        X=$?; rm -rf __src___WORK; exit $X"""
    },
    "python2.6": {
        "name": "Python %s",
        "executable": "python2.6",
        "lang": "py",
        "find_version": "%s 2>&1 --version | sed 's/^Python //'",
        "run": "__compiler__ __src__"
    },
    "python2.7": {
        "name": "Python %s",
        "executable": "python2.7",
        "lang": "py",
        "find_version": "%s 2>&1 --version | sed 's/^Python //'",
        "run": "__compiler__ __src__"
    },
    "python3.2": {
        "name": "Python %s",
        "executable": "python3.2",
        "lang": "py",
        "find_version": "%s 2>&1 --version | sed 's/^Python //'",
        "run": "__compiler__ __src__"
    },
    "python3.3": {
        "name": "Python %s",
        "executable": "python3.3",
        "lang": "py",
        "find_version": "%s 2>&1 --version | sed 's/^Python //'",
        "run": "__compiler__ __src__"
    },
    "python3.4": {
        "name": "Python %s",
        "executable": "python3.4",
        "lang": "py",
        "find_version": "%s 2>&1 --version | sed 's/^Python //'",
        "run": "__compiler__ __src__"
    },
    "python3.5": {
        "name": "Python %s",
        "executable": "python3.5",
        "lang": "py",
        "find_version": "%s 2>&1 --version | sed 's/^Python //'",
        "run": "__compiler__ __src__"
    },
    "python3.6": {
        "name": "Python %s",
        "executable": "python3.6",
        "lang": "py",
        "find_version": "%s 2>&1 --version | sed 's/^Python //'",
        "run": "__compiler__ __src__"
    },
    "ghc": {
        "name": "Glasgow Haskell Compiler %s",
        "executable": "ghc",
        "lang": "hs",
        "find_version": "%s --version | sed 's/^.*version //'",
        "build": "__compiler__ --make __src__ -O2 -Wall -outputdir=ghcdumps -o __exe__"
    }
}

def detect_compilers():
    """Detect and insert to database available compilers"""
    from distutils.spawn import find_executable
    path = os.environ['PATH']
    if app.config.get('PATH_EXTRA'): # pragma: no cover
        path = path + os.pathsep + os.pathsep.join(app.config.get('PATH_EXTRA'))
    for compilerid in detectable_compilers:
        compiler = detectable_compilers[compilerid]
        executable = find_executable(compiler['executable'], path=path)
        if executable:
            run = compiler.get("run", "__exe__") \
                    .replace("__compiler__", executable) \
                    .replace("__src__", "%src%") \
                    .replace("__exe__", "%exe%")
            build = compiler.get("build", "") \
                    .replace("__compiler__", executable) \
                    .replace("__src__", "%src%") \
                    .replace("__exe__", "%exe%")
            if compiler.get('find_version'):
                proc = subprocess.Popen(compiler['find_version'] % executable,
                                     shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                ver = proc.communicate()[0].decode().strip(' \t\n\r')
            else:
                ver = "" # pragma: no cover

            name = compiler['name'] % ver
            comp = Compiler.query.filter(Compiler.autodetect == compilerid).first() or Compiler()
            comp.name = name
            comp.lang = compiler.get('lang')
            comp.cmd_compile = build
            comp.cmd_run = run
            comp.autodetect = compilerid
            comp.executable = compiler['executable']
            db.session.add(comp)
    db.session.commit()
