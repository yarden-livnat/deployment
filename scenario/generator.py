import random
import xml.etree.ElementTree as ET

from .eg23 import scheduler

# RANDOM_SEED = 0
RANDOM_SEED = None

VARS = [
    # {
    #     'name': 'sfr_eff',
    #     'pattern': ".//*[name='{}']//eff".format('sfr_reprocessing'),
    #     'range': [0.99, 0.999]
    # },
    # {
    #     'name': 'uox_eff',
    #     'pattern': ".//*[name='{}']//eff".format('uox_reprocessing'),
    #     'range': [0.99, 0.999]
    # },
    {
        'name': 'breeding',
        'range': [1.02, 1.3]
    },
    {
        'name': 'bias',
        'range': [0, 0.1]
    },
    {
        'name': 'transition',
        'irange': [50, 80],
    },
    {
        'name': 'fr_start',
        'irange': [80, 110],
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
        Generator.xml_set_values(parent, 'build_times', schedule.when)
        Generator.xml_set_values(parent, 'n_build', schedule.num)
        Generator.xml_set_values(parent, 'prototypes', schedule.what)

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
            setattr(spec, var['name'], value)

    def create_demand(self, d, rate, years):
        self.demand = [d]*51
        for year in range(51, years+80):
            d = d*rate
            self.demand.append(d)

    def collect(self, name):
        spec = {}
        reactor = self.scenario.find(".//*[name='{}']".format(name))
        spec['lifetime'] = int(reactor.find('lifetime').text) // 12
        spec['cycle_time'] = int(reactor.find('.//cycle_time').text)
        spec['refuel_time'] = int(reactor.find('.//refuel_time').text)
        spec['assem_size'] = int(reactor.find('.//assem_size').text)
        spec['n_assem_core'] = int(reactor.find('.//n_assem_core').text)
        spec['n_assem_batch'] = int(reactor.find('.//n_assem_batch').text)
        spec['capacity'] = float(reactor.find('.//power_cap').text)

        if name in ['lwr', 'fr']:
            recipe_name = reactor.find(".//fuel_outrecipes/val").text
            recipe = self.scenario.find(f".//*[name=\'{recipe_name}\']")
            total = 0
            pu = 0
            for nucid in recipe.findall('.//nuclide'):
                val = float(nucid.find('.//comp').text)
                total += val
                if nucid.find('./id').text.startswith('Pu'):
                    pu += val
            spec['pu_out'] = pu/total

        # if name == 'fr':
        #     mixer = self.spec.find(".//*[@name=['sfr_mixer']")
        #     recipe_name = reactor.find(".//fuel_inrecipes/val").text
        #     print(name, 'in:', recipe_name)
        #     recipe = self.scenario.find(f".//*[name=\'{recipe_name}\']")
        #     total = 0
        #     pu = 0
        #     for nucid in recipe.findall('.//nuclide'):
        #         val = float(nucid.find('.//comp').text)
        #         total += val
        #         if nucid.find('./id').text.startswith('Pu'):
        #             pu += val
        #     spec['pu_out'] = pu / total
        return spec

    def init(self):
        random.seed(None)

        self.header = [var['name'] for var in VARS]

        self.spec = Spec()
        self.spec.years = int(self.scenario.find('.//duration').text) // 12
        self.spec.rate = self.rate

        self.spec.legacy_lwr_0 = self.collect('legacy_lwr_0')
        self.spec.legacy_lwr_1 = self.collect('legacy_lwr_1')
        self.spec.lwr = self.collect('lwr')
        self.spec.fr = self.collect('fr')

        self.spec.sfr_eff = 0.998
        self.spec.uox_eff = 0.998

        self.create_demand(self.ns.initial_demand, self.spec.rate, self.spec.years)
        self.spec.demand = self.demand

    def adapt_sfr_waste_pu(self):
        elem = self.scenario.find(".//*[name='sfr_mixer']")
        ratio = elem.find('.//mixing_ratio').text
        sfr_mixer_ratio = float(ratio)
        self.spec.fr['pu_in'] = sfr_mixer_ratio
        waste_pu = self.spec.breeding * sfr_mixer_ratio
        self.spec.fr['pu_out'] = waste_pu
        # print(f'waste pu: {waste_pu} = {sfr_mixer_ratio} * {self.spec.breeding}')

        total = 0
        nucid = dict()
        recipe = self.scenario.find(f".//*[name='sfr_waste_recipe']")
        for elem in recipe.findall('.//nuclide'):
            nid = elem.find('./id').text
            val = float(elem.find('.//comp').text)
            # print(f'nuid: {nid}  val: {val}')
            nucid[nid] = val
            total += val
        for nid in nucid:
            nucid[nid] /= total

        change = waste_pu - nucid['Pu239']
        nucid['Pu239'] = waste_pu
        nucid["U238"] -= change

        for elem in recipe.findall('.//nuclide'):
            nid = elem.find('./id').text
            elem.find('.//comp').text = str(nucid[nid])

    def author(self, logfile):
        self.spec.logfile = logfile
        self.select_values(self.spec)
        self.adapt_sfr_waste_pu()

        nodes = self.scenario.findall(".//*[name='{}']//build_times/val".format('recycling_inst'))
        for node in nodes:
            node.text = str(self.spec.transition*12)

        lwr, fr = scheduler(self.spec)

        lwr_deploy = self.scenario.find(".//*[name='{}']/config/DeployInst".format('lwr_inst'))
        self.set_schedule(lwr_deploy, lwr)

        fr_deploy = self.scenario.find(".//*[name='{}']/config/DeployInst".format('fr_inst'))
        self.set_schedule(fr_deploy, fr)

        for var in VARS:
            if var['name'] in ['transition', 'fr_start']:
                var['value'] += 1950

        return self.scenario, [str(var['value']) for var in VARS]




