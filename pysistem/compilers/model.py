from pysistem import db
import subprocess
import tempfile
import hashlib
import os
import shlex

class Compiler(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80))
    lang = db.Column(db.String(80))
    cmd_compile = db.Column(db.String(8192))
    cmd_run = db.Column(db.String(8192))

    submissions = db.relationship('Submission', back_populates='compiler')

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

        input_file = open(input_path, 'w')
        input_file.write(stdin)
        input_file.close()

        cmd = shlex.split(self.cmd_run.replace('%exe%', exe).replace('%src%', src_path))
        cmd = ['runsbox', str(time_limit), str(memory_limit), input_path, '/dev/stdout'] + cmd

        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
        
        os.remove(input_path)
        return (p.returncode, stdout or b'', stderr or b'')