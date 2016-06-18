#!/usr/bin/python3
import zipfile
import pickle
import gzip
import io
import argparse
import xml.etree.ElementTree as ET
import sys
import fnmatch

def ext_to_compiler(ext):
    if ext == 'dpr':
        return 'pas'
    return ext

parser = argparse.ArgumentParser(description='Convert Contester problem ZIP file to PySistem .pysistem.gz file')
parser.add_argument('contesterzip', type=str, help='A Contester ZIP for conversion')
parser.add_argument('-o', '--output', type=str, help='Output file. Default=<problemname>.pysistem.gz')
parser.add_argument('-l', '--language', type=str, help='Language to use. Default=ru', default='ru', choices=('en', 'ru'))
parser.add_argument('-e', '--encoding', type=str, help='Encoding to use. Default=windows-1251', default='windows-1251')

args = parser.parse_args()

if not zipfile.is_zipfile(args.contesterzip):
    print('%s is not a ZIP file' % args.contesterzip, file=sys.stderr)
    sys.exit(1)

zf = zipfile.ZipFile(args.contesterzip, mode='r')

# Determining problem name
problem_name = None
for name in zf.namelist():
    if name[-4:] == '.xml':
        problem_name = name[:-4]
        break

if problem_name is None:
    print('Could not determine problem name. Possibly invalid archive', file=sys.stderr)
    sys.exit(1)

root = ET.fromstring(zf.read(problem_name + '.xml').decode(args.encoding))

info = {}
info['checkers'] = []

for child in root:
    if child.tag.lower() == 'name':
        if child.attrib.get('lang', args.language) == args.language:
            info['name'] = child.text

    elif child.tag.lower() == 'timelimit':
        if child.attrib.get('platform', 'native') == 'native':
            info['time_limit'] = int(child.text)

    elif child.tag.lower() == 'memorylimit':
        if child.attrib.get('platform', 'native') == 'native':
            info['memory_limit'] = int(child.text)

    elif child.tag.lower() == 'statement':
        if child.attrib.get('lang', args.language) == args.language:
            info['statement'] = zf.read(child.attrib.get('src')).decode(args.encoding)

    elif child.tag.lower() == 'hint':
        if child.attrib.get('lang', args.language) == args.language:
            info['description'] = child.text

    elif child.tag.lower() == 'judge':
        for c in child:
            if c.tag.lower() == 'checker':
                source = c.attrib.get('src')
                source_text = zf.read(source).decode(args.encoding)
                if source:
                    info['checkers'].append({
                        'name': source,
                        'compiler': ext_to_compiler(source.split('.')[-1]),
                        'source': source_text
                    })

    elif child.tag.lower() == 'testlist':
        inp = child.attrib.get('inputmask', 'tests/%s_*_input.txt' % problem_name).lower()
        pat = child.attrib.get('patternmask', 'tests/%s_*_pattern.txt' % problem_name).lower()

        tests_input = []
        tests_pattern = []

        for name in sorted(zf.namelist()):
            if fnmatch.fnmatch(name.lower(), inp):
                tests_input.append(zf.read(name).decode(args.encoding))
            elif fnmatch.fnmatch(name.lower(), pat):
                tests_pattern.append(zf.read(name).decode(args.encoding))

        if len(tests_pattern) < len(tests_input):
            tests_pattern = [''] * len(tests_input)

        info['test_groups'] = [{
            'score': 0,
            'score_per_test': 1,
            'check_all': False,
            'test_pairs': [{
                'input': tests_input[i], 
                'pattern': tests_pattern[i]
            } for i in range(len(tests_input))]
        }]

info['version'] = 3

to_write = pickle.dumps(info)
out = io.BytesIO()
with gzip.GzipFile(fileobj=out, mode='wb') as f:
    f.write(to_write)

result = out.getvalue()

if args.output:
    with open(args.output, 'wb') as f:
        f.write(result)
else:
    with open(problem_name + '.pysistem.gz', 'wb') as f:
        f.write(result)
