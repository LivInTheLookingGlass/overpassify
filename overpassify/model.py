from functools import singledispatch


class BlackBox(object):
    """This is the API provided by OverpassQL. To us, a black box"""
    globe = set()  # This is what we'll use to describe the entire map as a set

    @staticmethod
    def isWay(an_object):
        return True or False  # this is a total black box, based on internal typing

    @staticmethod
    def isNode(an_object):
        return True or False  # this is a total black box, based on internal typing

    @staticmethod
    def isArea(an_object):
        return True or False  # this is a total black box, based on internal typing

    @staticmethod
    def isRelation(an_object):
        return True or False  # this is a total black box, based on internal typing

    @staticmethod
    def getByTypeAndID(type_, ID):
        """Returns a set of all data which has that ID, filtered by type"""
        return BlackBox.globe[ID][type_]

    @staticmethod
    def getByID(ID):
        """Returns a set of all data which has that ID, regardless of type"""
        return BlackBox.globe[ID]

    @staticmethod
    def search(an_object, **kwargs):
        data = an_object
        if isinstance(an_object, Area):
            data = Set(BlackBox.searchInArea(an_object))
        return Set(BlackBox.filterByKeys(data, **kwargs))

    @staticmethod
    def filterByKeys(data, **kwargs):
        ret = set()
        for item in data.data:
            for key, value in kwargs:
                if value == item[key]:
                    ret.add(item)
        return ret

    @staticmethod
    def searchInSet(a_set, **kwargs):
        """An approximation of the API feature which searches in an existing set"""
        data = set()
        for item in a_set:
            for key, value in kwargs:
                if value == item[key]:
                    data.add(item)
        return data

    @staticmethod
    def searchInArea(an_area):
        """An approximation of the API feature which searches in an area"""
        return {item for item in an_area.contents()}  # black box

    @staticmethod
    def around(*args):
        """An approximation of the API feature which searches around a set"""
        data = set()
        if len(args) == 2:
            some_set, radius = args
            for item in BlackBox.globe:
                for reference in some_set:
                    if BlackBox.distance(item, reference) < radius:
                        data.add(item)
                        break
        elif len(args) == 3:
            radius, lat, lon = args
            for item in BlackBox.globe:
                if BlackBox.distance(item, lat, lon) < radius:
                    data.add(item)
        else:
            raise ValueError('Not given appropriate arguments')
        return data


class Regex(object):
    def __init__(self, rule):
        self.comparer = re.compile(rule)

    def __eq__(self, target):
        return (self.comparer.match(target) is not None)


class NotRegex(Regex):
    def __eq__(self, target):
        return not super(NotRegex, self).__eq__(target)


class Set(object):
    """This is the standard container object. It can contain all OverpassQL non-primitives"""
    def __init__(self, *args):
        self.data = {*arg for arg in args}

    def __add__(self, target):
        if isinstance(target, Set):
            return Set(self, target)
        else:
            raise TypeError('Cannot add Set and {}'.format(target))

    def __iter__(self):
        """Iterates over all items in the set, as single item sets"""
        return (type(self)([datum]) for datum in self.data)


class SpecializedSet(Set):
    @singledispatch
    def __init__(self, query, **kwargs):
        data = SpecializedSet.parse_query(query)
        data = BlackBox.search(data, **kwargs)
        data = type(self).filter(data)
        super(SpecializedSet, self).__init__(data)

    @staticmethod
    def parse_query(query):
        if isinstance(query, int):
            return set([BlackBox.getByID(query)])
        elif isinstance(query, Set):
            return query
        else:
            raise TypeError('Cannot feed this type of value to parse_query: {}'.format(query))


    def __add__(self, target, cls=None):
        if cls is None:
            cls = type(self)
        if isinstance(target, cls):
            return cls._create(self.data, target.data)
        else:
            mro = inspect.getmro(self)
            cls = mro[mro.index(cls) + 1]
            cls.__add__(self, target, cls=cls)


class Way(SpecializedSet):
    @staticmethod
    def filter(some_set):
        ret = set()
        for item in some_set:
            if BlackBox.isWay(item):
                ret.add(item)
        return ret


class Node(SpecializedSet):
    @staticmethod
    def filter(some_set):
        ret = set()
        for item in some_set:
            if BlackBox.isNode(item):
                ret.add(item)
        return ret


class Area(SpecializedSet):
    @staticmethod
    def filter(some_set):
        ret = set()
        for item in some_set:
            if BlackBox.isArea(item):
                ret.add(item)
        return ret


class Relation(SpecializedSet):
    @staticmethod
    def filter(some_set):
        ret = set()
        for item in some_set:
            if BlackBox.isRelation(item):
                ret.add(item)
        return ret
