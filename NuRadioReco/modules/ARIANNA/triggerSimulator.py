from NuRadioReco.utilities import units
from NuRadioReco.framework.parameters import stationParameters as stnp
from NuRadioReco.framework.trigger import HighLowTrigger
import numpy as np
import time
import logging
logger = logging.getLogger('ARIANNAtriggerSimulator')


class triggerSimulator:
    """
    Calculates the trigger of an event.
    Uses the ARIANNA trigger logic, that a single antenna needs to cross a high and a low threshold value,
    and then coincidences between antennas can be required.
    """

    def __init__(self):
        self.__t = 0
        self.begin()

    def begin(self, samples_before_trigger=50):
        self.__samples_before_trigger = samples_before_trigger

    def run(self, evt, station, det,
            threshold_high=60 * units.mV,
            threshold_low=-60 * units.mV,
            high_low_window=20 * units.ns,
            coinc_window=32 * units.ns,
            number_concidences=2,
            triggered_channels=[0, 1, 2, 3],
            cut_trace=True,
            trigger_name="default_high_low",
            set_not_triggered=False):
        """
        simulate ARIANNA trigger logic

        Parameters
        ----------
        threshold_high: float
            the threshold voltage that needs to be crossed on a single channel on the high side
        threshold_low: float
            the threshold voltage that needs to be crossed on a single channel on the low side
        high_low_window: float
           time window in which a high+low crossing needs to occur to trigger a channel
        coinc_window: float
            time window in which number_concidences channels need to trigger
        number_concidences: int
            number of channels that are requried in coincidence to trigger a station
        triggered_channels: array of ints
            channels ids that are triggered on
        cut_trace: bool
            if true, trace is cut to the correct length (50ns before the trigger,
            max trace length is set according to detector description) 
        trigger_name: string
            a unique name of this particular trigger
        set_not_triggered: bool (default: False)
            if True not trigger simulation will be performed and this trigger will be set to not_triggered
            
        """
        t = time.time()
        if threshold_low >= threshold_high:
            logger.error("Impossible trigger configuration, high {0} low {1}.".format(threshold_high, threshold_low))
            raise NotImplementedError

        sampling_rate = station.get_channels()[0].get_sampling_rate()
        if not set_not_triggered:
            trigger = {}
            max_signal = 0
    
            for channel in station.get_channels():
                channel_id = channel.get_id()
                if channel_id not in triggered_channels:
                    continue
                trace = channel.get_trace()
                trigger[channel_id] = []
                max_signal = max(max_signal, np.max(np.abs(trace)))
    
                low_sample = 0
                high_sample = 0
                for sm in range(trace.shape[0]):
                    if ((trace[sm] > threshold_high)):
                        if (((sm - low_sample) < (high_low_window * sampling_rate)) and (low_sample != 0)):
                            trigger[channel_id].append(sm)
                        high_sample = sm
                    if (trace[sm] < threshold_low):
                        if (((sm - high_sample) < (high_low_window * sampling_rate)) and (high_sample != 0)):
                            trigger[channel_id].append(sm)
                        low_sample = sm
    
            station.set_parameter(stnp.channels_max_amplitude, max_signal)
            has_triggered = False
            trigger_time_sample = None
            # loop over the trace with a sliding window of "coinc_window"
            coinc_window_samples = np.int(np.round(coinc_window * sampling_rate))
            trace_length = len(station.get_channels()[0].get_trace())
            for i in range(0, trace_length - coinc_window_samples):
                istop = i + coinc_window_samples
                coinc = 0
                trigger_times = []
                for iCh, tr in trigger.items():  # loops through triggers of each channel
                    tr = np.array(tr)
                    mask_trigger_in_coind_window = (tr >= i) & (tr < istop)
                    if(np.sum(mask_trigger_in_coind_window)):
                        coinc += 1
                        # save time/sample of first trigger in coincidence window
                        trigger_times.append(tr[mask_trigger_in_coind_window][0])
                if coinc >= number_concidences:
                    has_triggered = True
                    trigger_time_sample = min(trigger_times)
                    break
        else:
            logger.info("set_not_triggered flag True, setting triggered to False.")
            has_triggered = False
    
    #         coinc = 0
    #         for ch1 in trigger.keys()[:-1]:
    #             for ch2 in range(ch1 + 1, n_channels):
    #                 for tr1 in trigger[ch1]:
    #                     for tr2 in trigger[ch2]:
    #                         if abs(tr1 - tr2) < coinc_window / sampling_rate:
    #                             coinc += 1

        trigger = HighLowTrigger(trigger_name, threshold_high, threshold_low, high_low_window,
                                 coinc_window, channels=triggered_channels,  number_of_coincidences=number_concidences)

        if not has_triggered:
            trigger.set_triggered(False)
            logger.info("Station has NOT passed trigger")
            trigger_time_sample = self.__samples_before_trigger
            trigger.set_trigger_time(trigger_time_sample / sampling_rate)
        else:
            trigger.set_triggered(True)
            trigger.set_trigger_time(trigger_time_sample / sampling_rate)
            logger.info("Station has passed trigger, trigger time is {:.1f} ns (sample {})".format(
                trigger.get_trigger_time() / units.ns, trigger_time_sample))

        station.set_trigger(trigger)

        if not cut_trace:
            self.__t += time.time() - t
            return

        # now cut trace to the correct number of samples
        # assuming that all channels have the same trace length
        for channel in station.get_channels():
            trace = channel.get_trace()
            trace_length = len(trace)
            number_of_samples = det.get_number_of_samples(station.get_id(), channel.get_id())
            if number_of_samples > trace.shape[0]:
                logger.error("Input has fewer samples than desired output. Channels has only {} samples but {} samples are requested.".format(
                    trace.shape[0], number_of_samples))
#                 new_trace = np.zeros(self.number_of_samples)
#                 new_trace[:trace.shape[0]] = trace
#                 change_time = 0
                raise StandardError
#             elif number_of_samples == trace.shape[0]:
#                 logger.info("Channel {} already at desired length, nothing done.".format(channel.get_id()))
            else:
                rel_station_time_samples = 0
                cut_samples_beginning = 0
                if(self.__samples_before_trigger < trigger_time_sample):
                    cut_samples_beginning = trigger_time_sample - self.__samples_before_trigger
                    if(cut_samples_beginning + number_of_samples > trace_length):
                        logger.warning("trigger time is sample {} but total trace length is only {} samples (requested trace length is {} with an offest of {} before trigger). To achieve desired configuration, trace will be rolled".format(
                            trigger_time_sample, trace_length, number_of_samples, self.__samples_before_trigger))
                        roll_by = cut_samples_beginning + number_of_samples - trace_length  # roll_by is positive
                        trace = np.roll(trace, -1 * roll_by)
                        cut_samples_beginning -= roll_by
                    rel_station_time_samples = cut_samples_beginning
                elif(self.__samples_before_trigger > trigger_time_sample):
                    roll_by = trigger_time_sample - self.__samples_before_trigger
                    logger.warning(
                        "trigger time is before 'trigger offset window', the trace needs to be rolled by {} samples first".format(roll_by))
                    trace = np.roll(trace, roll_by)
                    trigger_time_sample -= roll_by
                    rel_station_time_samples = -roll_by

                # shift trace to be in the correct location for cutting
                trace = trace[cut_samples_beginning:(number_of_samples + cut_samples_beginning)]
                channel.set_trace(trace, channel.get_sampling_rate())
        try:
            logger.debug('setting ssim tation start time to {:.1f} + {:.1f}ns'.format(
                station.get_sim_station().get_trace_start_time(), (rel_station_time_samples / sampling_rate)))
            # here we assumed that all channels had the same length
            station.get_sim_station().add_trace_start_time(-rel_station_time_samples / sampling_rate)
        except:
            logger.warning("No simulation information in event, trace start time will not be added")
        self.__t += time.time() - t

    def end(self):
        from datetime import timedelta
        logger.setLevel(logging.INFO)
        dt = timedelta(seconds=self.__t)
        logger.info("total time used by this module is {}".format(dt))
        return dt
