import NuRadioReco.framework.event
import NuRadioReco.framework.station
from NuRadioReco.framework.parameters import showerParameters as shP
from NuRadioReco.framework.parameters import stationParameters as stP
from NuRadioReco.framework.parameters import electricFieldParameters as efp

from NuRadioReco.modules.io.coreas import coreas

from NuRadioReco.utilities import units

from radiotools import helper as hp

import h5py
import numpy as np
import time
import re

import logging
logger = logging.getLogger('readCoREASShower')


class readCoREASShower:

    def __init__(self):
        self.__t = 0
        self.__t_event_structure = 0
        self.__t_per_event = 0

    def begin(self, input_files, verbose=False, read_in_highlevel_file=False):
        """
        begin method

        initialize readCoREASShower module

        Parameters
        ----------
        input_files: input files
            list of coreas hdf5 files
        """
        self.__input_files = input_files
        self.__current_input_file = 0
        self.__verbose = verbose

        self.__highlevel = read_in_highlevel_file

    def run(self):
        """
        read in a full CoREAS simulation

        """
        while (self.__current_input_file < len(self.__input_files)):
            t = time.time()
            t_per_event = time.time()

            # filesize = os.path.getsize(self.__input_files[self.__current_input_file])
            # if(filesize < 18456 * 2):
            #     logger.warning("file {} seems to be corrupt, skipping to next file".format(
            #            self.__input_files[self.__current_input_file]))
            #     self.__current_input_file += 1
            #     continue

            if self.__verbose:
                print('Reading %s ...' % self.__input_files[self.__current_input_file])

            corsika = h5py.File(self.__input_files[self.__current_input_file], "r")
            logger.info("using coreas simulation {} with E={:2g} theta = {:.0f}".format(
                self.__input_files[self.__current_input_file], corsika['inputs'].attrs["ERANGE"][0] * units.GeV,
                corsika['inputs'].attrs["THETAP"][0]))

            f_coreas = corsika["CoREAS"]

            evt = NuRadioReco.framework.event.Event(corsika['inputs'].attrs['RUNNR'], corsika['inputs'].attrs['EVTNR'])
            evt.__event_time = f_coreas.attrs["GPSSecs"]

            sim_shower = coreas.make_sim_shower(corsika)
            sim_shower.set_parameter(shP.core, np.array([0, 0, f_coreas.attrs["CoreCoordinateVertical"] / 100]))  # overwrite core
            evt.add_sim_shower(sim_shower)

            if self.__highlevel:
                try:
                    f_highlevel = corsika["highlevel"]
                except KeyError:
                    logger.KeyError("No highlevel group")
                    raise ValueError("No highlevel group")

                # choose first one, rest is read latter
                planes = list(f_highlevel.keys())
                obs_plane = f_highlevel[planes[0]]

                # in case simulation is not a star shaped
                try:
                    # evt.set_parameter("radiation_energy_1D", obs_plane.attrs["radiation_energy_1D"] * units.eV)
                    evt.set_parameter(shP.radiation_energy, obs_plane.attrs["radiation_energy"] * units.eV)
                except KeyError:
                    pass

                antenna_position = obs_plane["antenna_position"]
                antenna_position_vBvvB = obs_plane["antenna_position_vBvvB"]
                energy_fluence = obs_plane["energy_fluence"]
                energy_fluence_vector = obs_plane["energy_fluence_vector"]
                frequency_slope = obs_plane["frequency_slope"]
                names = obs_plane["antenna_names"]

                # later parse station id from antenna name if possible
                for idx, pos in enumerate(np.array(antenna_position)):

                    station_id = antenna_id(names[idx], idx)  # return proper station id if possible
                    station = NuRadioReco.framework.station.Station(station_id)

                    sim_station = NuRadioReco.framework.sim_station.SimStation(station_id, position=pos)
                    electric_field = NuRadioReco.framework.electric_field.ElectricField([0, 1, 2])
                    electric_field.set_parameter(efp.ray_path_type, 'direct')
                    sim_station.set_parameter(efp.signal_energy_fluence, energy_fluence_vector[idx])

                    sim_station.add_electric_field(electric_field)
                    # sim_station.set_parameter(stP.position_vB_vvB, antenna_position_vBvvB[idx])
                    # sim_station.set_parameter(stP.signal_energy_fluence, energy_fluence[idx])
                    # sim_station.set_parameter(efp.frequency_slope, frequency_slope[idx])

                    station.set_sim_station(sim_station)
                    evt.set_station(station)

            else:
                for idx, (name, observer) in enumerate(f_coreas['observers'].items()):
                    station_id = antenna_id(name, idx)  # return proper station id if possible

                    station = NuRadioReco.framework.station.Station(station_id)
                    sim_station = coreas.make_sim_station(station_id, corsika, observer, channel_ids=[0, 1, 2])

                    station.set_sim_station(sim_station)
                    evt.set_station(station)

            self.__t_per_event += time.time() - t_per_event
            self.__t += time.time() - t

            self.__current_input_file += 1

            yield evt

    def end(self):
        from datetime import timedelta
        logger.setLevel(logging.INFO)
        dt = timedelta(seconds=self.__t)
        logger.info("total time used by this module is {}".format(dt))
        logger.info("\tcreate event structure {}".format(timedelta(seconds=self.__t_event_structure)))
        logger.info("\per event {}".format(timedelta(seconds=self.__t_per_event)))
        return dt


def antenna_id(antenna_name, default_id):
    """
    This function parses the antenna name given in a CoREAS simulation and tries to find an ID
    It can be extended to other name patterns
    """

    if re.match("AERA_", antenna_name):
        new_id = int(antenna_name.strip("AERA_"))
        return new_id
    else:
        return default_id
