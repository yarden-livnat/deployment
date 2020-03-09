import sys
import csv
import argparse
import sqlite3

nuc_names = ['U', 'Np', 'Pu', 'Am', 'Cm']

INITIAL_DEMAND = 10000


def create_demand(d, rate, years):
    demand = [2000 * (y//4 + 1) for y in range(20)]

    for year in range(20, years):
        d = d*rate
        demand.append(d)
    return demand


def total_power(c, row, header):
    c.execute('''select tl.year, ifnull(p.power, 0) as power from
                (select distinct (time-1)/12 as year from timelist )as tl
                left join (
                    select time/12 as year, sum(value)/12 as power from TimeSeriesPower group by year
                ) as p on tl.year = p.year''')
    total = c.fetchone()
    row.append(total[0])


def excess(c, row, header):
    rate = float(row[header.index('rate')])

    c.execute('''select ifnull(p.power, 0) as power from
                    (select distinct (time-1)/12 as year from timelist )as tl
                    left join (
                        select (time-1)/12 as year, sum(value)/12 as power from TimeSeriesPower group by year
                    ) as p on tl.year = p.year''')
    power_series = c.fetchall()

    years = len(power_series)
    demand = create_demand(INITIAL_DEMAND, rate, years)
    total = 0
    max_per_year = None
    for year in range(years):
        e = power_series[year][0] - demand[year]
        total += e
        max_per_year = max(max_per_year, e) if max_per_year is not None else e
    row.append(total)
    row.append(max_per_year)


def waste(c, row, header):
    c.execute('''select SUM(inv.Quantity * c.MassFrac) AS qty, c.nucid /10000000 as id
                from
                (select * 
                    from Inventories 
                    where agentid in (select agentid from agents where prototype = 'sink')
                        and starttime <= (select max(time) from timelist) and endtime > (select max(time) from timelist)
                ) as  inv
                join (select nucid, MassFrac, qualid from Compositions where nucid >= 920000000) as c on c.qualid = inv.qualid
                group by id
        ''')
    waste_series = c.fetchall()

    w = [0] * len(nuc_names)
    last = 92 + len(nuc_names)
    for qty, id in waste_series:
        if id < last:
            w[id-92] = qty
    row.extend(w)


measures = [
    # {'measures': 'total_power', 'f': total_power},

    {'measures': ['excess', 'max_excess'], 'f': excess},
    {'measures': ['waste_' + name for name in nuc_names], 'f': waste}
]


def parse(args):
    p = argparse.ArgumentParser(prog='post', description='post processing')
    p.add_argument('db', default='cyclus', help="database")
    p.add_argument('report', default='report.csv', help='report.csv file')
    p.add_argument('-o', '--output', dest='output', default='statistics.csv', help='output file')
    return p.parse_args(args)


def run(args=None):
    args = sys.argv[1:] if args is None else args
    ns = parse(args)

    with open(ns.output, 'w') as out:
        writer = csv.writer(out)

        with open(ns.report) as f:
            reader = csv.reader(f)

            header = next(reader)
            for measure in measures:
                names = measure['measures']
                if type(names) == str:
                    header.append(names)
                else:
                    header.extend(names)
            writer.writerow(header)

            for row in reader:
                db = '{}.{}.sqlite'.format(ns.db, row[0])
                print('db:', db)
                conn = sqlite3.connect(db)
                c = conn.cursor()

                for measure in measures:
                    measure['f'](c, row, header)

                writer.writerow(row)

                conn.close()


if __name__ == '__main__':
    run()