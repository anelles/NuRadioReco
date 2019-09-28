from __future__ import absolute_import, division, print_function
import NuRadioReco.framework.base_station
import numpy as np
from six import iteritems
try:
    import cPickle as pickle
except ImportError:
    import pickle
import logging
logger = logging.getLogger('SimStation')


class SimStation(NuRadioReco.framework.base_station.BaseStation):

    def __init__(self, station_id, sampling_rate=None, trace=None, position=None):
        NuRadioReco.framework.base_station.BaseStation.__init__(self, station_id, position)
        self.__magnetic_field_vector = None
        self.__simulation_weight = None
        if(trace is not None and sampling_rate is not None):
            self.set_electric_fields(trace, sampling_rate)

    def get_magnetic_field_vector(self):
        return self.__magnetic_field_vector

    def set_magnetic_field_vector(self, magnetic_field_vector):
        self.__magnetic_field_vector = magnetic_field_vector

    def get_simulation_weight(self):
        return self.__simulation_weight

    def set_simulation_weight(self, simulation_weight):
        self.__simulation_weight = simulation_weight

    def get_axis_distance(self):
        if not self.has_parameter(astP.position_vB_vvB):
            logger.error("sim station position in vB vvB v system is not set")
            raise ValueError("sim station position in vB vvB v system is not set")

        position_vB_vvB = self.get_parameter(astP.position_vB_vvB)
        return np.sqrt(position_vB_vvB[0] ** 2 + position_vB_vvB[1] ** 2)

    def serialize(self, mode):
        base_station_pkl = NuRadioReco.framework.base_station.BaseStation.serialize(self, mode)
        data = {'__magnetic_field_vector': self.__magnetic_field_vector,
                '__simulation_weight': self.__simulation_weight,
                'base_station': base_station_pkl}
        return pickle.dumps(data, protocol=4)

    def deserialize(self, data_pkl):
        data = pickle.loads(data_pkl)
        NuRadioReco.framework.base_station.BaseStation.deserialize(self, data['base_station'])
        self.__magnetic_field_vector = data['__magnetic_field_vector']
        self.__simulation_weight = data['__simulation_weight']
