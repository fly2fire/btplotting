import itertools
from collections import defaultdict

import backtrader as bt


def get_plot_objs(strategy, include_non_plotable=False,
                  order_by_plotmaster=False):
    '''
    Returns all plotable objects of a strategy

    By default the result will be ordered by the
    data the object is aligned to. If order_by_plotmastere
    is True, objects will be aligned to their plotmaster.
    '''
    datas = strategy.datas
    inds = strategy.getindicators()
    obs = strategy.getobservers()
    objs = defaultdict(list)
    # ensure strategy is included
    objs[strategy] = []
    # first loop through datas
    for d in datas:
        if not include_non_plotable and not d.plotinfo.plot:
            continue
        objs[d] = []
    # next loop through all ind and obs and set them to
    # the corresponding data clock
    for obj in itertools.chain(inds, obs):
        if not hasattr(obj, 'plotinfo'):
            # no plotting support cause no plotinfo attribute
            # available - so far LineSingle derived classes
            continue
        # should this indicator be plotted?
        if (not include_non_plotable
                and (not obj.plotinfo.plot or obj.plotinfo.plotskip)):
            continue
        # append object to the data object
        data = get_clock_obj(obj, True)
        if data in objs:
            objs[data].append(obj)

    if not order_by_plotmaster:
        return objs
    
    # order objects by its plotmaster
    pobjs = defaultdict(list)
    for d in objs:
        pmaster = get_plotmaster(d)
        if pmaster is d and pmaster not in pobjs:
            pobjs[pmaster] = []
        elif pmaster is not d:
            pobjs[pmaster].append(d)
        for o in objs[d]:
            # subplot = create a new figure for this indicator
            subplot = o.plotinfo.subplot
            if subplot and o not in pobjs:
                pobjs[o] = []
            elif not subplot:
                pmaster = get_plotmaster(get_clock_obj(o, True))
                pobjs[pmaster].append(o)
    # return objects ordered by plotmaster
    return pobjs
    '''
    datas = strategy.datas
    inds = strategy.getindicators()
    obs = strategy.getobservers()
    objs = defaultdict(list)
    # ensure strategy is included
    objs[strategy] = []
    # first loop through datas
    for d in datas:
        pmaster = get_plotmaster(d.plotinfo.plotmaster)
        if (not d.plotinfo.plot
                or (pmaster and not pmaster.plotinfo.plot)):
            continue
        pmaster = get_plotmaster(d.plotinfo.plotmaster)
        # if no plotmaster then data is plotmaster
        if pmaster is None:
            objs[d] = []
        else:
            objs[pmaster].append(d)
    # next loop through all ind and obs and set them to
    # the corresponding data clock
    for obj in itertools.chain(inds, obs):
        if not hasattr(obj, 'plotinfo'):
            # no plotting support cause no plotinfo attribute
            # available - so far LineSingle derived classes
            continue

        # should this indicator be plotted?
        if not obj.plotinfo.plot or obj.plotinfo.plotskip:
            continue

        # subplot = create a new figure for this indicator
        subplot = obj.plotinfo.subplot
        pmaster = get_plotmaster(get_clock_obj(obj, True))

        if subplot and pmaster is None:
            objs[obj] = []
        else:
            if pmaster is None:
                pmaster = get_plotmaster(obj)
            if pmaster not in objs:
                continue
            objs[pmaster].append(obj)

    return objs
    '''


def get_plotmaster(obj):
    '''
    Resolves the plotmaster of the given object
    '''
    if obj is None:
        return None

    while True:
        pm = obj.plotinfo.plotmaster
        if pm is None:
            break
        else:
            obj = pm
    return obj


def get_last_avail_idx(strategy, dataname=False):
    '''
    Returns the last available index of a data source
    '''
    if dataname is not False:
        data = strategy.getdatabyname(dataname)
    else:
        data = strategy
    offset = 0
    while True:
        if len(data) > offset and data.datetime[-offset] != data.datetime[-offset]:
            offset += 1
            continue
        break
    return len(data) - 1 - offset


def filter_by_dataname(obj, dataname):
    '''
    Returns if the given object should be included
    True if it should be included, False if not
    '''
    if dataname is False:
        return True

    obj_dataname = get_dataname(obj)
    return obj_dataname is False or obj_dataname == dataname


def get_datanames(strategy, filter=True):
    '''
    Returns the names of all data sources
    '''
    datanames = []
    for d in strategy.datas:
        if not filter or d.plotinfo.plot is not False:
            datanames.append(get_dataname(d))
    return datanames


def get_dataname(obj):
    '''
    Returns the name of the data for the given object
    If the data for a object is a strategy then False will
    be returned.
    '''
    data = get_clock_obj(obj, True)
    if isinstance(data, bt.Strategy):
        # strategy will have no dataname
        return False
    elif isinstance(data, bt.AbstractDataBase):
        # data feeds are end points
        # try some popular attributes that might carry a name
        # _name: user assigned value upon instantiation
        # _dataname: underlying bt dataname (is always available)
        # if that fails, use str
        for n in ['_name', '_dataname']:
            val = getattr(data, n)
            if val is not None:
                break
        if val is None:
            val = str(data)
        return val
    else:
        raise Exception(
            f'Unsupported data: {obj.__class__}')


def get_clock_obj(obj, resolv_to_data=False):
    '''
    Returns a clock object to use for building data
    A clock object can be either a strategy, data source,
    indicator or a observer.
    '''
    if isinstance(obj, bt.LinesOperation):
        # indicators can be created to run on a line
        # (instead of e.g. a data object) in that case grab
        # the owner of that line to find the corresponding clock
        # also check for line actions like "macd > data[0]"
        return get_clock_obj(obj._clock, resolv_to_data)
    elif isinstance(obj, bt.LineSingle):
        # if we have a line, return its owners clock
        return get_clock_obj(obj._owner, resolv_to_data)
    elif isinstance(obj, bt.LineSeriesStub):
        # if its a LineSeriesStub object, take the first line
        # and get the clock from it
        return get_clock_obj(obj.lines[0], resolv_to_data)
    elif isinstance(obj, (bt.IndicatorBase, bt.ObserverBase)):
        # a indicator and observer can be a clock, internally
        # it is obj._clock
        if resolv_to_data:
            return get_clock_obj(obj._clock, resolv_to_data)
        clk = obj
    elif isinstance(obj, bt.StrategyBase):
        # a strategy can be a clock, internally it is obj.data
        clk = obj
    elif isinstance(obj, bt.AbstractDataBase):
        clk = obj
    else:
        raise Exception(
            f'Unsupported clock: {obj.__class__}')
    return clk


def get_clock_line(obj):
    '''
    Find the corresponding clock for an object.
    A clock is a datetime line that holds timestamps
    for the line in question.
    '''
    clk = get_clock_obj(obj)
    return clk.lines.datetime


def get_source_id(source):
    '''
    Returns a unique source id for given source.
    This is used for unique column names.
    '''
    return str(id(source))
