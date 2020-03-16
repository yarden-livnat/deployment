import random
import xml.etree.ElementTree as ET

from .eg23 import scheduler

# RANDOM_SEED = 0
RANDOM_SEED = None

VARS = [
    {'name': 'sfr_eff',
     'pattern': ".//*[name='{}']//eff".format('sfr_reprocessing'),
     # 'values': [0.9, 0.99, 0.999],
     'range': [0.9, 0.999]
    },

    {'name': 'uox_eff',
     'pattern': ".//*[name='{}']//eff".format('uox_reprocessing'),
     'range': [0.9, 0.999]
     # 'values': [0.9, 0.99, 0.999],
    },

    # {'name': 'tails_assay',
    #  'pattern': './/*/Enrichment/tails_assay',
    #  'range': [0.001, 0.005],
    # },

    {'name': 'lwr_fr',
     'range': [2, 4],
    
     },

    {'name': 'fr_fr',
     'range': [7, 10],
     },

    {'name': 'fr_start',
     'irange': [91, 140],
    
     },

    {'name': 'lookahead',
     'irange': [1, 2]
     }
]


class Spec(object):
    pass


class Generator(object):
    def __init__(self, ns):
        self.ns = ns
        self.template = ET.parse(ns.template_file)
        self.scenario = self.template.getroot()
        self.demand = []
        self.header = []
        self.spec = None
        self.rate = 1.01
        self.init()

    @staticmethod
    def xml_set_values(parent, name, values):
        parent.remove(parent.find(name))
        node = ET.SubElement(parent, name)

        for value in values:
            val = ET.SubElement(node, 'val')
            val.text = str(value)

    @staticmethod
    def set_schedule(parent, schedule):
        when, num, what = schedule
        Generator.xml_set_values(parent, 'build_times', when)
        Generator.xml_set_values(parent, 'n_build', num)
        Generator.xml_set_values(parent, 'prototypes', what)

    def select_values(self, spec):
        for var in VARS:
            value = None
            if 'values' in var:
                values = var['values']
                value = values[random.randrange(0, len(values))]
            elif 'range' in var:
                values = var['range']
                value = random.uniform(values[0], values[1])
            elif 'irange' in var:
                values = var['irange']
                value = random.randrange(values[0], values[1])

            var['value'] = value
            if 'pattern' in var:
                nodes = self.scenario.findall(var['pattern'])
                for node in nodes:
                    node.text = str(value)
            else:
                setattr(spec, var['name'], value)

    def create_demand(self, d, rate, years):
        self.demand = [d]*56
        for year in range(56, years+100):
            d = d*rate
            self.demand.append(d)

    def init(self):
        random.seed(RANDOM_SEED)
        self.header = [var['name'] for var in VARS]

        self.spec = Spec()
        self.spec.years = int(self.scenario.find('.//duration').text) // 12
        self.spec.rate = self.rate

        lwr = self.scenario.find(".//*[name='{}']".format('lwr'))
        lwr_cap = float(lwr.find('.//power_cap').text)
        lwr_lifetime = int(lwr.find('lifetime').text)//12

        fr = self.scenario.find(".//*[name='{}']".format('fr'))
        fr_cap = float(fr.find('.//power_cap').text)
        fr_lifetime = int(fr.find('lifetime').text) // 12

        self.spec.capacity = lwr_cap, fr_cap
        self.spec.lifetime = lwr_lifetime, fr_lifetime

        self.create_demand(self.ns.initial_demand, self.spec.rate, self.spec.years)
        self.spec.demand = self.demand

    def author(self, logfile):
        lwr_units = [0] * self.spec.years
        fr_units = [0] * self.spec.years
        self.spec.supply = lwr_units, fr_units
        self.spec.logfile = logfile
        self.select_values(self.spec)
        lwr, fr = scheduler(self.spec)

        lwr_deploy = self.scenario.find(".//*[name='{}']/config/DeployInst".format('lwr_inst'))
        self.set_schedule(lwr_deploy, lwr)

        fr_deploy = self.scenario.find(".//*[name='{}']/config/DeployInst".format('fr_inst'))
        self.set_schedule(fr_deploy, fr)

        return self.scenario, [str(var['value']) for var in VARS]




