import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d
import os
from radiotools import helper as hp
from NuRadioReco.utilities import units, io_utilities
import logging
logger = logging.getLogger('analog_components')


def load_amp_response(amp_type='rno-surface', path=os.path.dirname(os.path.realpath(__file__))):  # here we use log data
    """
    Read out amplifier gain and phase. Currently only examples have been implemented.
    Needs a better structure in the future, possibly with database.
    """
    amp_response = {}
    if amp_type == 'rno-surface':
        ph = os.path.join(path, 'HardwareResponses/surface_-60dBm_chan0_LogA_20dB.csv')
        ff = np.loadtxt(ph, delimiter=',', skiprows=7, usecols=(0))
        amp_gain_discrete = np.loadtxt(ph, delimiter=',', skiprows=7, usecols= (5))
        amp_phase_discrete = np.loadtxt(ph, delimiter=',', skiprows=7, usecols= (6))
    if amp_type == 'iglu':
        ph = os.path.join(path, 'HardwareResponses/iglu_drab_chan0_-60dBm_LogA_20dB.csv')
        ff = np.loadtxt(ph, delimiter=',', skiprows=7, usecols=(0))
        amp_gain_discrete = np.loadtxt(ph, delimiter=',', skiprows=7, usecols= (5))
        amp_phase_discrete = np.loadtxt(ph, delimiter=',', skiprows=7, usecols= (6))
    else:
        logger.error("Amp type not recognized")
        return amp_response

    # Convert to GHz and add 20dB for attenuation in measurement circuit
    ff *= units.Hz

    if amp_type == 'rno-surface' or amp_type == 'iglu':
        amp_gain_discrete += 20
    amp_gain_db_f = interp1d(ff, amp_gain_discrete, bounds_error=False, fill_value=1)
    # all requests outside of measurement range are set to 0

    def get_amp_gain(ff):
        amp_gain_db = amp_gain_db_f(ff)
        amp_gain = 10 ** (amp_gain_db / 20.)  #convert from db to lin scale
        return amp_gain

    # Convert to MHz and broaden range
    amp_phase_f = interp1d(ff, np.unwrap(amp_phase_discrete * units.degree),
                           bounds_error=False, fill_value=0)  # all requests outside of measurement range are set to 0

    def get_amp_phase(ff):
        amp_phase = amp_phase_f(ff)
        return amp_phase

    amp_response['gain'] = get_amp_gain
    amp_response['phase'] = get_amp_phase

    def get_amp_response(ff):
        return print(amp_response['gain'](ff) * np.exp(1j * amp_response['phase'](ff)))

    return amp_response

def load_amp_measurement(amp_measurement='surface_-60dBm_chan0_RI_20dB'):  # here we use Real and Imaginary
    """
    load individual amp measurement from file and buffer interpolation function
    """
    amp_measures = {}
    filename = os.path.join(os.path.dirname(__file__), 'HardwareResponses/', amp_measurement+".csv")
    ff = np.loadtxt(filename, delimiter=',', skiprows=7, usecols=0) # frequency
    ff *= units.Hz
    response_re = np.loadtxt(filename, delimiter=',', skiprows=7, usecols=5) # real part
    response_im = np.loadtxt(filename, delimiter=',', skiprows=7, usecols=6) # imaginary part
    response = response_re + response_im * 1j
    phase = np.unwrap(np.angle(response, deg=False))
    gain_db = (20 * np.log10(abs(response)))+20 #db
    gain = 10 ** (gain_db / 20.)

    amp_phase_f = interp1d(ff, phase, bounds_error=False, fill_value=0)  # all requests outside of measurement range are set to 0
    amp_gain_f = interp1d(ff, gain, bounds_error=False, fill_value=1)  # all requests outside of measurement range are set to 1

    amp_measures['gain'] = amp_gain_f
    amp_measures['phase'] = amp_phase_f

    def get_amp_measure(ff):
        return print(amp_measures['gain'](ff) * np.exp(1j * amp_measures['phase'](ff)))

    return amp_measures
