from __future__ import absolute_import, division, print_function, unicode_literals
from NuRadioReco.modules.io import ARIANNAio
import logging
logger = logging.getLogger('eventReader')


class eventReader:
    """
    save events to file
    """

    def begin(self, filename):
        self.__fin = ARIANNAio.ARIANNAio(filename, parse_header=False)

    def run(self):
        return self.__fin.get_events()

    def end(self):
        self.__fin.close_file()
