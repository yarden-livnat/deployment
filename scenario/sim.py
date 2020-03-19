import os
import sys
import subprocess
import argparse
import csv
import xml.etree.ElementTree as ET
from xml.dom import minidom
from pathlib import Path
import time

from .generator import Generator
from .measures import Measures


def save(filename, scenario):
    xml_str = minidom.parseString(ET.tostring(scenario)).toprettyxml(indent="", newl="")
    with open(filename, 'w') as f:
        f.write(xml_str)


def parse(args):
    p = argparse.ArgumentParser(prog='scenario', description='Cyclus scenario generator')
    p.add_argument('-j', '--job', default='1', type=int, dest='job', help='jobid')
    p.add_argument('-t', '--template', default='template.json', dest='template_file', help='template file')
    p.add_argument('-o', '--output', default='simulations', dest='output', help='output directory')
    p.add_argument('-s', '--offset', default='0', type=int, dest='offset', help='first output number')

    p.add_argument('-n', '--samples', default=1, dest='samples', type=int, help='number of scenarios to generate')

    p.add_argument('-d', '--demand', default='100000', type=float, dest='initial_demand', help='initial demand')
    p.add_argument('-r', '--report', default='params.csv',  dest='report', help='report file')
    ns = p.parse_args(args)
    return ns


def sim(args=None):
    args = sys.argv[1:] if args is None else args
    ns = parse(args)
    path = Path(ns.output) / str(ns.job)
    path.mkdir(parents=True, exist_ok=True)

    generator = Generator(ns)
    measures = Measures(generator.demand)

    xml_filename = str(path / 'scenario.xml')
    db = str(path / 'cyclus.sqlite')
    log = open(str(path / 'log'), 'w')

    with open(path / ns.report, 'w') as f:
        report = csv.writer(f)
        report.writerow(generator.header + measures.header)

    for i in range(ns.samples):
        print(f'sim {ns.job}-{i}')
        os.system('rm -f '+db)

        # print('\tcreate...', end="")
        # t = time.time()
        scenario, params = generator.author(path / f'scheduler_{i}_log.csv')
        save(xml_filename, scenario)
        # print("{:.3f}".format(time.time() - t))

        # print('\tcyclus...', end="")
        # t = time.time()
        subprocess.run(['cyclus', xml_filename, '-o', db], check=True, stdout=log, stderr=log, universal_newlines=True)
        # print("{:.3f}".format(time.time()-t))
        #
        # # print('\tpost...', end="")
        # # t = time.time()
        # # subprocess.run(['cyan', '-db', db, 'post'], check=True, stdout=log, stderr=log)
        # # print("{:.3f}".format(time.time()-t))
        #
        # print('\tmeasures...', end="")
        # t = time.time()
        values, data = measures.compute(db)
        # print(f'{ns.job} sim: {i} {time.time()-t:.1f}')

        with open(path / ns.report, 'a') as f:
            report = csv.writer(f)
            report.writerow(params + values)

        with open(path / f'power-{i}.csv', 'w') as f:
            writer = csv.writer(f)
            writer.writerow(['year', 'power', 'prototype'])
            writer.writerow(data)


if __name__ == '__main__':
    sim()
