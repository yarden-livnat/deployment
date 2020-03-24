import sqlite3
import pandas as pd
nuc_names = ['U', 'Pu', 'Am']
# nuc_names = ['U', 'Np', 'Pu', 'Am', 'Cm']


def total_power(c, row, header):
    c.execute(''' select time/12 as year, sum(value)/12 as power from TimeSeriesPower group by year''')
    total = c.fetchone()
    row.append(total[0])


def power_ratio(c, row, header, demand):
    c.execute('''select sum(value) 
                   from TimeSeriesPower, AgentEntry
                   where TimeSeriesPower.AgentId == AgentEntry.AgentId 
                        and AgentEntry.Prototype == "fr" 
                        and time > 600
                    ''')
    fr = c.fetchone()[0]

    c.execute('''select sum(value) from TimeSeriesPower 
                    where time > 600''')
    total = c.fetchone()[0]

    row.append(1-fr/total)


def pu_to_power(c, row, header, demand):
    c.execute('''select time, sum(value) from TimeSeriesPower 
                       where time >= 600
                       group by time''')
    power = pd.DataFrame(c.fetchall(), columns=['month', 'power']).set_index('month')

    c.execute('''select time, sum(Quantity)
                         from ExplicitInventory
                         where NucId/10000000 == 94
                         and time >= 600
                         group by time''')
    rows = c.fetchall()

    pu = pd.DataFrame(rows, columns=['month', 'quantity']).set_index('month')

    ratios = pu.div(power['power'], axis=0)

    row.append(ratios.max().values)
    row.append(ratios.mean().values)


# def excess(c, row, header, demand):
#     c.execute('''select ifnull(p.power, 0) as power from
#                     (select distinct (time-1)/12 as year from timelist) as tl
#                     left join (
#                         select (time-1)/12 as year, sum(value)/12 as power from TimeSeriesPower group by year
#                     ) as p on tl.year = p.year''')
#     power_series = c.fetchall()
#
#     years = len(power_series)
#     total = 0
#     max_per_year = None
#
#     for year in range(years):
#         e = power_series[year][0] - demand[year]
#         total += e
#         max_per_year = max(max_per_year, e) if max_per_year is not None else e
#     row.append(total)
#     row.append(max_per_year)


def waste(c, row, header, *args):
    c.execute('''select NucId /10000000 as nid, Sum(Quantity)
                 from ExplicitInventory, AgentEntry
                 where (nid = 92 or nid = 94 or nid= 95)
                 and Time == (select duration -1 from info)
                 and ExplicitInventory.AgentID = AgentEntry.AgentId
                 and AgentEntry.Prototype != 'enrichment'
                 group by nid ''')
    waste_series = c.fetchall()

    w = [entry[1] for entry in waste_series]
    row.extend(w)


def power_per_year(c):
    c.execute('''select (time)/12 as year, sum(value)/12 as power, AgentEntry.Prototype as prototype 
                from TimeSeriesPower, AgentEntry
                where TimeSeriesPower.AgentId == AgentEntry.AgentId 
                group by year, prototype
                ''')
    power = c.fetchall()

    return power


MEASURES = [

    {'measures': 'power_ratio', 'f': power_ratio},
    {'measures': nuc_names, 'f': waste},
    {'measures': ['max_Pu2P', 'mean_Pu2P'], 'f': pu_to_power  },
    # {'measures': 'total_power', 'f': total_power},
    # {'measures': ['excess', 'max_excess'], 'f': excess},
    # {'measures': ['waste_' + name for name in nuc_names], 'f': waste}

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
