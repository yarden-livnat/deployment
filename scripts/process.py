import sys
import csv
import argparse
from pathlib import Path


def error(msg):
    print(msg)
    exit(255)


def get_measure(header, col=None, name=None):
    if name is not None:
        if name in header:
            col = header.index(name)
        else:
            error('Unknown measure: {}'.format(name))
    else:
        if col is None:
            col = len(header)-1
        elif col >= len(header):
            error('Measure col is out of bound')
        name = header[col]
    return name, col


def save(path, header, data, dims, col):
    measure = header[col]
    dest = path / measure
    if not dest.exists():
        dest.mkdir()
    output = dest / 'data.csv'

    with output.open("w") as o:
        writer = csv.writer(o)

        h = header[:dims]
        h.append(header[col])
        writer.writerow(h)

        for row in data:
            writer.writerow(row[:dims] + [row[col]])


def process(args=None):
    args = sys.argv[1:] if args is None else args
    ns = parse(args)

    with open(ns.filename) as f:
        reader = csv.reader(f)
        header = next(reader)

        data = []
        for row in reader:
            data.append(row)

        path = Path(ns.filename).parent

        if ns.all:
            for col in range(ns.dims, len(header)):
                save(path, header, data, ns.dims, col)
        else:
            measure, col = get_measure(header, col=ns.col, name=ns.name)
            save(path, header, data, ns.dims, col)


def parse(args):
    p = argparse.ArgumentParser(prog='analyze', description='Extract input dimension and a single measure')
    p.add_argument('filename', help='data.csv file')
    p.add_argument('-d', type=int, dest='dims', required=True, help="num of input dimensions")
    p.add_argument('-c', type=int, dest='col', default=None, help="the column of the output measure")
    p.add_argument('-m', dest='name', default=None, help="name of measure to use")
    p.add_argument('--all', action='store_true', help='extract all measures')
    return p.parse_args(args)


if __name__ == '__main__':
    process()