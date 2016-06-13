# -*- coding: utf-8 -*-
from pysistem import app, db
import subprocess
import tempfile
import hashlib
import os
import shlex
from time import sleep

class Compiler(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80))
    lang = db.Column(db.String(80))
    cmd_compile = db.Column(db.String(8192))
    cmd_run = db.Column(db.String(8192))
    autodetect = db.Column(db.String(16))
    executable = db.Column(db.String(80))

    submissions = db.relationship('Submission', cascade = "all,delete", backref='compiler')

    def __init__(self, name=None, lang=None, cmd_compile=None, cmd_run=None):
        self.name = name
        self.lang = lang
        self.cmd_compile = cmd_compile
        self.cmd_run = cmd_run

    def __repr__(self):
        return '<Compiler %r>' % self.name

    def compile(self, src, exe):
        cmd = self.cmd_compile.replace('%exe%', exe).replace('%src%', src)
        result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        return (result.returncode == 0, result.stdout or '')

    def run(self, exe, src_path='', time_limit=1000, memory_limit=65536, stdin=''):
        hasher = hashlib.new('md5')
        hasher.update(str.encode(exe))
        input_path = tempfile.gettempdir() + '/pysistem_runner_input_' + str(self.id) + hasher.hexdigest()

        with open(input_path, 'w') as input_file:
            input_file.write(stdin)

        output_path = tempfile.gettempdir() + '/pysistem_runner_output_' + str(self.id) + hasher.hexdigest()

        cmd = shlex.split(self.cmd_run.replace('%exe%', exe).replace('%src%', src_path))
        cmd = ['runsbox', str(time_limit), str(memory_limit), input_path, output_path] + cmd

        if os.path.exists('/SANDBOX'):
            p = subprocess.Popen(cmd, cwd='/SANDBOX')
        else:
            p = subprocess.Popen(cmd)
        p.wait()
        stdout = b''
        with open(output_path, "rb") as output_file:
            stdout = output_file.read()
        
        os.remove(input_path)
        os.remove(output_path)
        return (p.returncode, stdout, b'')

    def is_available(self):
        from distutils.spawn import find_executable
        path = os.environ['PATH']
        if app.config.get('PATH_EXTRA'):
            path = path + os.pathsep + os.pathsep.join(app.config.get('PATH_EXTRA'))
        if (find_executable(self.executable, path=path)):
            return True
        else:
            return False

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
        "build": "mkdir __src___WORK && __compiler__ __src__ -FE__src___WORK \
        && cp __src___WORK/`basename __src__ .pas` __exe__; X=$?; rm -r __src___WORK; exit $X"
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
}

def detect_compilers():
    from distutils.spawn import find_executable
    path = os.environ['PATH']
    if app.config.get('PATH_EXTRA'):
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
                p = subprocess.Popen(compiler['find_version'] % executable,
                    shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                ver = p.communicate()[0].decode().strip(' \t\n\r')
            else:
                ver = ""

            name = compiler['name'] % ver
            c = Compiler.query.filter(Compiler.autodetect == compilerid).first() or Compiler()
            c.name = name
            c.lang = compiler.get('lang')
            c.cmd_compile = build
            c.cmd_run = run
            c.autodetect = compilerid
            c.executable = compiler['executable']
            db.session.add(c)
    db.session.commit()