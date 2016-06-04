from pysistem import db
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
        result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return (result.returncode == 0, result.stdout or '', result.stderr or '')

    def run(self, exe, src_path='', time_limit=1000, memory_limit=65536, stdin=''):
        hasher = hashlib.new('md5')
        hasher.update(str.encode(exe))
        input_path = tempfile.gettempdir() + '/pysistem_runner_input_' + str(self.id) + hasher.hexdigest()

        with open(input_path, 'w') as input_file:
            input_file.write(stdin)

        output_path = tempfile.gettempdir() + '/pysistem_runner_output_' + str(self.id) + hasher.hexdigest()

        cmd = shlex.split(self.cmd_run.replace('%exe%', exe).replace('%src%', src_path))
        cmd = ['runsbox', str(time_limit), str(memory_limit), input_path, output_path] + cmd

        p = subprocess.Popen(cmd)
        p.wait()
        stdout = b''
        with open(output_path, "rb") as output_file:
            stdout = output_file.read()
        
        os.remove(input_path)
        os.remove(output_path)
        return (p.returncode, stdout, b'')