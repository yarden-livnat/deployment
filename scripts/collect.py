import csv
import argparse
from pathlib import Path
import re
import pandas as pd

pattern = re.compile('power-(\d+)')

data = []


def process(ns):
    count = ns.s
    for d in ns.dirs:
        count = process_dir(Path(d), count, Path(ns.out))
        print('*** count:', count)

    datafile = Path(ns.out) / 'deployment.csv'
    with datafile.open(mode='w') as f:
        writer = csv.writer(f)
        writer.writerow(['sfr_eff', 'uox_eff', 'breeding', 'bias', 'fr_start', 'power_ratio', 'U', 'Np', 'Pu', 'Am', 'Cm'])
        writer.writerows(data)


def process_dir(path, offset, out):
    print('dir:', path)
    i = 1
    while True:
        d = path / str(i)
        print(d)
        if d.exists():
            offset = process_files(d, offset, out)
            i += 1
        else:
            break

    return offset


def process_files(path, offset, out):
    n = 0
    params = path / 'params.csv'
    with params.open() as f:
        reader = csv.reader(f)
        next(reader)
        for line in reader:
            data.append(line)
            n += 1

    # power files
    for i in range(n):
        filename = path / f'power-{i}.csv'
        if not filename.exists():
            print('missing file ', filename)
            continue

        with filename.open() as f:
            f.readline()
            line = f.readline()
        lines = re.compile('"\((\d+), ([\d,\.]+), \\\'([a-z,_,0-9]+)\\\'\)"').findall(line)

        outfile = Path(out) / f'power-{offset+i:05}.csv'
        with outfile.open(mode='w') as f:
            w = csv.writer(f)
            w.writerow(['year', 'power', 'prototype'])
            for y, p, t in lines:
                w.writerow([y, p, t])

    # schedule files
    for i in range(n):
        filename = path / f'scheduler_{i}_log.csv'
        if not filename.exists():
            print('missing file ', filename)
            continue
        schedule = []
        with filename.open() as f:
            f.readline()
            f.readline()
            for line in f:
                if not line.startswith('---'):
                    g = line.strip().split(',')
                    schedule.append([g[0], g[1], g[2]])

        outfile = Path(out) / f'schedule-{offset + i:05}.csv'
        with outfile.open(mode='w') as f:
            w = csv.writer(f)
            w.writerow(['year', 'lwr', 'fr'])
            for y, lwr, fr in schedule:
                w.writerow([y, lwr, fr])

    return offset + n


def parse(args=None):
    p = argparse.ArgumentParser(prog='fix', description='')
    p.add_argument('dirs', nargs='+')
    # p.add_argument('-d', '--dir', default='simulations', help='directory')
    p.add_argument('-s', type=int, default=0)
    p.add_argument('-o', '--out', default='results', help='output directory')

    return p.parse_args(args)


if __name__ == '__main__':
    process(parse())
