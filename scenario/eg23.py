from math import floor, ceil
import random
from pathlib import Path
from collections import defaultdict
import json


class Schedule:
    def __init__(self, kind):
        self.when = []
        self.what = []
        self.num = []
        self.kind = kind

    def add(self, when, what, num):
        self.when.append(when)
        self.what.append(what)
        self.num.append(num)


def legacy_schedule():
    path = Path('./legacy_schedule.json')

    if not path.exists():
        l0 = defaultdict(int)
        l1 = defaultdict(int)
        for i in range(50):
            l0[random.randint(0, 49)] += 1
            l1[random.randint(0, 49)] += 1

        build = sorted([(year, l0[year], 'legacy_lwr_0') for year in l0] +
                       [(year, l1[year], 'legacy_lwr_1') for year in l1],
                       key=lambda record: record[0])
        with open(path, mode='w') as f:
            json.dump(build, f)

    else:
        with open(path, mode='r') as f:
            build = json.load(f)

    return build


def scheduler(spec):
    lwr = Schedule('lwr')
    fr = Schedule('fr')

    demand = spec.demand

    lwr_decommission = [0] * (spec.years * 12)
    fr_decommission = [0] * (spec.years * 12)
    lwr_cap = spec.lwr['capacity']
    fr_cap = spec.fr['capacity']
    lwr_lifetime = spec.lwr['lifetime']
    fr_lifetime = spec.fr['lifetime']

    pu = [0]*((spec.years+100)*12)
    pu_stock = 0

    lwr_produces = spec.lwr['assem_size'] * spec.lwr['pu_out'] * spec.uox_eff

    fr_consumes = spec.fr['assem_size'] * spec.fr['pu_in']
    fr_construct = spec.fr['n_assem_core'] * fr_consumes
    fr_produces = spec.fr['assem_size'] * spec.fr['pu_out'] * spec.sfr_eff

    start_year = 1950
    transition_year = 2015 - 1950
    delay = 1 + 36 + 1 + 1 + 1
    # delays:
    #    1 to pool
    #   84 in pool
    #    1 to reprocessing
    #    1 to fab
    #    1 to reactor

    # first 50 years: half legacy_lwr_0 half legacy_lwr_1
    build = legacy_schedule()
    for y, n, prototype in build:
        lwr.add(when=y * 12+1, what=prototype, num=n)
        if prototype == 'legacy_lwr_0':
            lwr_decommission[y + spec.legacy_lwr_0['lifetime']] += n
        else:
            lwr_decommission[y + spec.legacy_lwr_1['lifetime']] += n

    n_lwr = 100
    n_fr = 0

    with open(spec.logfile, 'w') as log:
        log.write(f'cap: {lwr_cap} {fr_cap}  fr_start: {spec.fr_start} breeding:{spec.breeding} sfr_eff:{spec.sfr_eff} bias {spec.bias}\n')

        log.write('year, lwr,  fr, demand,    gap, fwd_gap, pu_stock, support, b_lwr, b_fr\n')
        for month in range(50*12, spec.years*12):
            # account for pu produced and consumed this month
            pu_stock += pu[month]
            # print(f'{month//12}/{month%12} new pu: {pu[month]:.0f}')

            # building new reactors can happen only once a year
            if month % 12 != 0:
                continue

            year = month // 12
            if year == transition_year:
                log.write('--- transition year --------\n')

            n_lwr -= lwr_decommission[year]
            n_fr -= fr_decommission[year]
            capacity = n_lwr * lwr_cap + n_fr * fr_cap

            can_build = floor(max(pu_stock, 0) / fr_construct)

            build_fr = 0
            build_lwr = 0

            gap_ratio = capacity / demand[year]
            fwd_gap = demand[year]*(1+spec.bias) - capacity
            if gap_ratio < (1 - spec.bias):
                if year >= spec.fr_start:
                    need = ceil(fwd_gap/fr_cap)
                    build_fr = min(need, can_build)
                build_lwr = max(ceil((fwd_gap - build_fr * fr_cap) / lwr_cap), 0)

            if build_lwr > 0 and year + lwr_lifetime < spec.years:
                lwr_decommission[year + lwr_lifetime] = build_lwr

            if build_fr > 0 and year + fr_lifetime < spec.years:
                fr_decommission[year + fr_lifetime] = build_fr

            if year == spec.fr_start:
                log.write('----fr available------------------\n')

            log.write(f'{year:3}, {n_lwr:3}, {n_fr:4}, {demand[year]:6.0f}, {demand[year]-capacity:6.0f}, {fwd_gap:6.0f}'
                      f'{pu_stock:7.0f} {can_build:8}, {build_lwr:4}, {build_fr:4}\n')

            if build_lwr > 0:
                if year < transition_year:
                    lwr.add(month, 'legacy_lwr_1', build_lwr)
                    # don't collect Pu before the transition year
                else:
                    lwr.add(month, 'lwr', build_lwr)
                    cycle_time = spec.lwr['cycle_time']
                    for m in range(cycle_time, lwr_lifetime * 12, cycle_time+1):
                        pu[month + m + delay] += lwr_produces * build_lwr
                n_lwr += build_lwr

            if build_fr > 0:
                n_fr += build_fr
                fr.add(month, 'fr', build_fr)

                cycle_time = spec.fr['cycle_time']
                for m in range(cycle_time, fr_lifetime*12, cycle_time+1):
                    pu[month+m] -= fr_consumes * build_fr            # required for regular operational
                    pu[month+m+delay] += fr_produces * build_fr      # produced after delay in pools

                pu_stock -= fr_construct * build_fr

    return lwr, fr
