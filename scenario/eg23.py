from math import floor, ceil


def scheduler(spec):
    lwr_when = []
    lwr_num = []
    lwr_what = []
    fr_when = []
    fr_num = []
    fr_what = []
    demand = spec.demand

    lwr_units, fr_units = spec.supply
    lwr_cap, fr_cap = spec.capacity
    lwr_lifetime, fr_lifetime = spec.lifetime

    n_lwr = 0
    n_fr = 0

    pu = [0]*((spec.years+100)*12)
    available_pu = 0
    # fr_consumes = 3 * 5867 * 0.128996341
    # lwr_produces = 30160 * 0.0130328
    # fr_produces = 5867 * (0.13102 / 0.128996341 - 1)
    fr_consumes = 3 * 5867 * 0.114198325
    lwr_produces = 30160 * 0.0118849 * 0.998
    fr_produces = 5867 * (0.1297121 * 0.998 - 0.114198325)
    transition_year = 2015 - 1959
    delay = 36

    with open(spec.logfile, 'w') as log:
        log.write(f'cap: {lwr_cap} {fr_cap}  ratio {spec.lwr_fr}  {spec.fr_fr}  lookahead {spec.lookahead}\n')
        log.write('year, lwr, fr, demand, capacity, support, b_lwr, b_fr\n')

        for month in range(spec.years*12):
            available_pu += pu[month]
            if month % 12 != 0:
                continue

            year = month // 12
            if year == transition_year:
                log.write('--- transition year --------\n')

            n_lwr += lwr_units[year]
            n_fr += fr_units[year]
            capacity = n_lwr * lwr_cap + n_fr * fr_cap

            can_support = floor(available_pu / fr_consumes)
            build_fr = 0
            build_lwr = 0
            if year < 51:
                build_lwr = 2
            else:
                gap = demand[year] - capacity
                fwd_gap = demand[year + spec.lookahead] - capacity
                if gap > 0:
                    if year >= spec.fr_start:
                        need = ceil(fwd_gap/fr_cap)
                        build_fr = min(need, can_support)
                    build_lwr = max(ceil((fwd_gap - build_fr * fr_cap) / lwr_cap), 0)

            if build_lwr > 0 and year + lwr_lifetime < spec.years:
                lwr_units[year + lwr_lifetime] -= build_lwr

            if build_fr > 0 and year + fr_lifetime < spec.years:
                fr_units[year + fr_lifetime] -= build_fr

            if year == spec.fr_start:
                log.write('----fr available------------------\n')
            log.write(f'{year:3}, {n_lwr:3}, {n_fr:4}, {demand[year]:6.0f}, {demand[year]-capacity:6.0f}, {can_support:8}, {build_lwr:4}, {build_fr:4}\n')

            n_lwr += build_lwr
            n_fr += build_fr

            if build_lwr > 0:
                lwr_when.append(month)
                lwr_num.append(build_lwr)
                lwr_what.append('lwr')
                if year > transition_year:
                    for m in range(18, lwr_lifetime*12, 18):
                        pu[month+m+delay] += lwr_produces * build_lwr

            if build_fr > 0:
                fr_when.append(month)
                fr_num.append(build_fr)
                fr_what.append('fr')
                for m in range(14, fr_lifetime*12, 14):
                    pu[month+m+delay] += fr_produces * build_fr
                available_pu -= fr_consumes * build_fr

    return [lwr_when, lwr_num, lwr_what], [fr_when, fr_num, fr_what]
