import sqlite3

nuc_names = ['U', 'Np', 'Pu', 'Am', 'Cm']


def total_power(c, row, header):
    c.execute(''' select time/12 as year, sum(value)/12 as power from TimeSeriesPower group by year''')
    total = c.fetchone()
    row.append(total[0])


def power_ratio(c, row, header, demand):
    c.execute('''select sum(value) 
                   from TimeSeriesPower, AgentEntry
                   where TimeSeriesPower.AgentId == AgentEntry.AgentId 
                        and AgentEntry.Prototype == "fr" 
                        and time > 780
                    ''')
    fr = c.fetchone()[0]

    c.execute('''select sum(value) from TimeSeriesPower ''')
    total = c.fetchone()[0]

    row.append(1-fr/total)


def excess(c, row, header, demand):
    c.execute('''select ifnull(p.power, 0) as power from
                    (select distinct (time-1)/12 as year from timelist) as tl
                    left join (
                        select (time-1)/12 as year, sum(value)/12 as power from TimeSeriesPower group by year
                    ) as p on tl.year = p.year''')
    power_series = c.fetchall()

    years = len(power_series)
    total = 0
    max_per_year = None
    for year in range(years):
        e = power_series[year][0] - demand[year]
        total += e
        max_per_year = max(max_per_year, e) if max_per_year is not None else e
    row.append(total)
    row.append(max_per_year)


def waste(c, row, header, *args):
    c.execute('''select NucId /10000000 as id, Sum(Quantity)
                 from ExplicitInventory
                 where NucId >= 920000000 and Time == (select duration -1 from info)
                 and ExplicitInventory.AgentId not in (select AgentId from AgentEntry where Prototype = "enrichment" )
                 group by id''')
    # c.execute('''select SUM(inv.Quantity * c.MassFrac) AS qty, c.nucid /10000000 as id
    #             from
    #             (select *
    #                 from Inventories
    #                 where agentid in (select agentid from agents where prototype = 'sink')
    #                     and starttime <= (select max(time) from timelist) and endtime > (select max(time) from timelist)
    #             ) as  inv
    #             join (select nucid, MassFrac, qualid from Compositions where nucid >= 920000000) as c on c.qualid = inv.qualid
    #             group by id
    #     ''')
    waste_series = c.fetchall()

    w = [0] * len(nuc_names)
    last = 92 + len(nuc_names)
    for nucid, qty in waste_series:
        if nucid < last:
            w[nucid-92] = qty
    row.extend(w)

import pandas as pd


def power_per_year(c):
    c.execute('''select time/12 as year, sum(value)/12 as power, AgentEntry.Prototype as prototype 
                from TimeSeriesPower, AgentEntry
                where TimeSeriesPower.AgentId == AgentEntry.AgentId 
                group by year, prototype
                ''')
    prototype = c.fetchall()

    return prototype


MEASURES = [
    # {'measures': 'total_power', 'f': total_power},
    {'measures': 'power_ratio', 'f': power_ratio},
    # {'measures': ['excess', 'max_excess'], 'f': excess},
    {'measures': ['waste_' + name for name in nuc_names], 'f': waste}
]


class Measures(object):
    def __init__(self, demand):
        self.demand = demand
        self.header = []

        for measure in MEASURES:
            names = measure['measures']
            if type(names) == str:
                self.header.append(names)
            else:
                self.header.extend(names)

    def compute(self, filename):
        conn = sqlite3.connect(filename)
        c = conn.cursor()

        c.execute('select duration from info')
        duration = c.fetchone()[0]
        c.execute('create table TimeList (time integer)')
        timeline = ",".join([f'({str(i)})' for i in range(duration)])
        c.execute(f'insert into TimeList  values {timeline}')
        conn.commit()

        values = []
        for measure in MEASURES:
            measure['f'](c, values, self.header, self.demand)

        power = power_per_year(c)
        conn.close()

        return values, power
