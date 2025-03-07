""" Basic scan functions.

This module contains test functions for basic scans, e.g. scan1D, scan2D, etc.
This is part of qtt.

"""

import sys
import tempfile
import warnings
from unittest import TestCase
from unittest.mock import MagicMock, patch

import numpy as np
import qcodes
import qcodes_loop.data.io
from qcodes import ManualParameter, Parameter
from qcodes_loop.data.data_set import DataSet
from qcodes.parameters import ScaledParameter

import qtt.algorithms.onedot
import qtt.gui.live_plotting
import qtt.instrument_drivers.gates
import qtt.utilities.tools
from qtt.instrument_drivers.simulation_instruments import SimulationDigitizer
from qtt.instrument_drivers.virtual_instruments import VirtualIVVI
from qtt.measurements.scans import (fastScan, get_instrument_parameter, get_sampling_frequency, instrumentName,
                                    measuresegment, sample_data_t, scan1D, scan2D, scanjob_t)
from qtt.structures import MultiParameter

if 1:  # prevent auto-formatting
    # mock to allow M4i import
    sys.modules['pyspcm'] = MagicMock()
    from qcodes_contrib_drivers.drivers.Spectrum.M4i import M4i
    del sys.modules['pyspcm']


class TestScans(TestCase):

    def setUp(self):
        DataSet.default_io = qcodes_loop.data.io.DiskIO(tempfile.mkdtemp(prefix='qtt-unittests'))

    def test_get_instrument_parameter(self):
        instrument = VirtualIVVI(instrumentName('test'), None)
        ix, p = get_instrument_parameter((instrument.name, 'dac2'))
        self.assertEqual(id(ix), id(instrument))
        self.assertEqual(id(p), id(instrument.dac2))
        ix, p = get_instrument_parameter((instrument, 'dac2'))
        self.assertEqual(id(p), id(instrument.dac2))
        ix, p = get_instrument_parameter(instrument.name + '.dac2')
        self.assertEqual(id(p), id(instrument.dac2))
        instrument.close()

    def test_sample_data(self):
        s = sample_data_t()
        s['gate_boundaries'] = {'D0': [-500, 100]}
        v = s.restrict_boundaries('D0', 1000)
        self.assertEqual(100, v)

    def test_scan1D(self, verbose=0):
        p = Parameter('p', set_cmd=None)
        q = Parameter('q', set_cmd=None)
        r = ScaledParameter(p, division=4)
        _ = MultiParameter(instrumentName('multi_param'), [p, q])

        gates = VirtualIVVI(
            name=qtt.measurements.scans.instrumentName('gates'), model=None)
        station = qcodes.Station(gates)
        station.gates = gates

        if verbose:
            print('test_scan1D: running scan1D')
        scanjob = scanjob_t({'sweepdata': dict(
            {'param': p, 'start': 0, 'end': 10, 'step': 2, 'wait_time': 0.}), 'minstrument': [r]})
        _ = scan1D(station, scanjob, liveplotwindow=False, verbose=0)

        scanjob = scanjob_t({'sweepdata': dict(
            {'param': p, 'start': 0, 'end': 10, 'step': 2, 'wait_time': 0.}), 'minstrument': [q, r]})
        _ = scan1D(station, scanjob, liveplotwindow=False, verbose=0)

        scanjob = scanjob_t({'sweepdata': dict(
            {'param': 'dac1', 'start': 0, 'end': 10, 'step': 2}), 'minstrument': [r]})
        _ = scan1D(station, scanjob, liveplotwindow=False, verbose=0)

        scanjob = scanjob_t({'sweepdata': dict(
            {'param': {'dac1': 1}, 'start': 0, 'range': 10, 'step': 2}), 'minstrument': [r]})
        data = scan1D(station, scanjob, liveplotwindow=False, verbose=0, extra_metadata={'hi': 'world'})
        self.assertTrue('hi' in data.metadata)
        gates.close()

    def test_scan1D_no_gates(self):
        p = Parameter('p', set_cmd=None)
        r = ScaledParameter(p, division=4)
        scanjob = scanjob_t({'sweepdata': {'param': p, 'start': 0, 'end': 10, 'step': 2}, 'minstrument': [r]})
        station = qcodes.Station()
        dataset = scan1D(station, scanjob, liveplotwindow=False, verbose=0)
        default_record_label = 'scan1D'
        self.assertTrue(default_record_label in dataset.location)

    def test_scanjob_record_label(self):
        p = Parameter('p', set_cmd=None)
        r = ScaledParameter(p, division=4)

        record_label = '123unittest123'
        scanjob = scanjob_t({'sweepdata': dict(
            {'param': p, 'start': 0, 'end': 10, 'step': 2, 'wait_time': 0.}), 'minstrument': [r]})
        scanjob['dataset_label'] = record_label
        station = qcodes.Station()
        dataset = scan1D(station, scanjob, liveplotwindow=False, verbose=0)
        self.assertTrue(dataset.location.endswith(record_label))

    def test_scan2D(self, verbose=0):
        p = Parameter('p', set_cmd=None)
        q = Parameter('q', set_cmd=None)
        r = ScaledParameter(p, division=4)
        _ = MultiParameter(instrumentName('multi_param'), [p, q])

        gates = VirtualIVVI(
            name=qtt.measurements.scans.instrumentName('gates'), model=None)
        station = qcodes.Station(gates)
        station.gates = gates

        if verbose:
            print('test_scan2D: running scan2D')
        scanjob = scanjob_t({'sweepdata': dict(
            {'param': p, 'start': 0, 'end': 10, 'step': 2}), 'minstrument': [r]})
        scanjob['stepdata'] = dict(
            {'param': q, 'start': 24, 'end': 30, 'step': 1.})
        _ = scan2D(station, scanjob, liveplotwindow=False, verbose=0)

        scanjob = scanjob_t({'sweepdata': dict({'param': {
            'dac1': 1, 'dac2': .1}, 'start': 0, 'range': 10, 'step': 2}), 'minstrument': [r]})
        scanjob['stepdata'] = dict(
            {'param': {'dac2': 1}, 'start': 24, 'range': 6, 'end': np.NaN, 'step': 1.})
        _ = scan2D(station, scanjob, liveplotwindow=False, verbose=0)

        scanjob = scanjob_t({'sweepdata': dict(
            {'param': {'dac1': 1}, 'start': 0, 'range': 10, 'step': 2}), 'minstrument': [r]})
        scanjob['stepdata'] = {'param': MultiParameter('multi_param', [gates.dac2, gates.dac3])}
        scanjob['stepvalues'] = np.array([[2 * i, 3 * i] for i in range(10)])
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                data = scan2D(station, scanjob, liveplotwindow=False, verbose=0)
        except Exception as ex:
            print(ex)
            warnings.warn('MultiParameter test failed!')
        # Test combination of Parameter and vector argument not supported:
        scanjob = scanjob_t({'sweepdata': dict({'param': {
            'dac1': 1}, 'start': 0, 'range': 10, 'step': 2, 'wait_time': 0.}), 'minstrument': [r]})
        scanjob['stepdata'] = dict(
            {'param': q, 'start': 24, 'range': 6, 'end': np.NaN, 'step': 1.})

        self.assertRaises(Exception, scan2D, station, scanjob, liveplotwindow=False, verbose=0)
        gates.close()

    def test_fastScan_no_awg(self):
        station = MagicMock()
        station.awg = None
        station.virtual_awg = None
        scanjob = scanjob_t({'sweepdata': dict({'param': {'dac1': 1},
                                                'start': 0,
                                                'range': 10,
                                                'step': 2}),
                             'minstrument': []})

        self.assertEqual(fastScan(scanjob, station), 0)

    @staticmethod
    def test_measure_segment_m4i_has_correct_output():
        expected_data = np.array([1, 2, 3, 4])
        waveform = {'bla': 1, 'ble': 2, 'blu': 3}
        number_of_averages = 100
        read_channels = [0, 1]

        with patch('qtt.measurements.scans.measuresegment_m4i') as measure_segment_mock:

            m4i_digitizer = M4i('test')
            measure_segment_mock.return_value = expected_data

            actual_data = measuresegment(waveform, number_of_averages, m4i_digitizer, read_channels)
            np.testing.assert_array_equal(actual_data, expected_data)
            measure_segment_mock.assert_called_with(m4i_digitizer, waveform, read_channels,
                                                    2000, number_of_averages, process=True)

            m4i_digitizer.close()

    @staticmethod
    def test_measure_segment_simulator_has_correct_output():
        expected_data = np.array([1, 2, 3, 4])
        waveform = {'bla': 1, 'ble': 2, 'blu': 3}
        number_of_averages = 100
        read_channels = [0, 1]

        with patch('qtt.instrument_drivers.simulation_instruments.SimulationDigitizer',
                   spec=SimulationDigitizer) as simulation_digitizer:

            simulation_digitizer.measuresegment.return_value = expected_data
            actual_data = measuresegment(waveform, number_of_averages, simulation_digitizer, read_channels)
            np.testing.assert_array_equal(actual_data, expected_data)
            simulation_digitizer.measuresegment.assert_called_with(waveform, channels=read_channels)

    def test_measure_segment_invalid_device(self):
        waveform = {'bla': 1, 'ble': 2, 'blu': 3}
        read_channels = [0, 1]

        self.assertRaises(Exception, measuresegment, waveform, 100, MagicMock(), read_channels)

    @staticmethod
    def test_measure_segment_no_data_raises_warning():
        expected_data = np.array([])
        waveform = {'bla': 1, 'ble': 2, 'blu': 3}
        number_of_averages = 100
        read_channels = [0, 1]

        with patch('qtt.instrument_drivers.simulation_instruments.SimulationDigitizer',
                   spec=SimulationDigitizer) as simulation_digitizer, patch('warnings.warn') as warn_mock:

            simulation_digitizer.measuresegment.return_value = expected_data
            actual_data = measuresegment(waveform, number_of_averages, simulation_digitizer, read_channels)
            warn_mock.assert_called_once_with('measuresegment: received empty data array')
            np.testing.assert_array_equal(expected_data, actual_data)

    def test_get_sampling_frequency_m4i(self):
        expected_value = 12.345e6

        m4i_digitizer = M4i('test')
        m4i_digitizer.sample_rate = ManualParameter('sample_rate', initial_value=expected_value)

        actual_value = get_sampling_frequency(m4i_digitizer)
        self.assertEqual(expected_value, actual_value)

        m4i_digitizer.close()

    def test_convert_scanjob_vec_scan1Dfast(self):
        p = Parameter('p', set_cmd=None)
        gates = VirtualIVVI(
            name=qtt.measurements.scans.instrumentName('gates'), model=None)
        station = qcodes.Station(gates)
        station.gates = gates

        # exclusive end-value
        scanjob = scanjob_t({'scantype': 'scan1Dfast', 'sweepdata': {'param': p, 'start': -2., 'end': 2., 'step': .4}})
        _, sweepvalues = scanjob._convert_scanjob_vec(station)
        actual_values = list(sweepvalues)
        expected_values = [-2.0, -1.6, -1.2, -0.8, -0.4, 0.0, 0.4, 0.8, 1.2, 1.6]
        for actual_val, expected_val in zip(actual_values, expected_values):
            self.assertAlmostEqual(actual_val, expected_val, 12)
        self.assertEqual(len(actual_values), 10)

        # exclusive: end - start < step
        scanjob = scanjob_t({'scantype': 'scan1Dfast',
                             'sweepdata': {'param': p, 'start': 20, 'end': 20.0050, 'step': .0075}})
        _, sweepvalues = scanjob._convert_scanjob_vec(station)
        actual_values = list(sweepvalues)
        expected_values = [20.0]
        for actual_val, expected_val in zip(actual_values, expected_values):
            self.assertAlmostEqual(actual_val, expected_val, 12)
        self.assertEqual(len(actual_values), 1)

        # inclusive end-value
        scanjob = scanjob_t({'scantype': 'scan1Dfast', 'sweepdata': {'param': p, 'start': -2., 'end': 2., 'step': .4}})
        _, sweepvalues = scanjob._convert_scanjob_vec(station, sweeplength=11)
        actual_values = list(sweepvalues)
        expected_values = [-2.0, -1.6, -1.2, -0.8, -0.4, 0.0, 0.4, 0.8, 1.2, 1.6, 2.0]
        for actual_val, expected_val in zip(actual_values, expected_values):
            self.assertAlmostEqual(actual_val, expected_val, 12)
        self.assertEqual(len(actual_values), 11)

        gates.close()

    def test_convert_scanjob_vec_scan1Dfast_range(self):
        gates = VirtualIVVI(
            name=qtt.measurements.scans.instrumentName('gates'), model=None)
        station = qcodes.Station(gates)
        station.gates = gates

        # exclusive end-value
        scanjob = scanjob_t({'scantype': 'scan1Dfast', 'sweepdata': {'param': 'dac1', 'range': 8, 'step': 2}})
        _, sweepvalues = scanjob._convert_scanjob_vec(station)
        actual_values = list(sweepvalues)
        expected_values = [-4.0, -2.0, 0.0, 2.0]
        for actual_val, expected_val in zip(actual_values, expected_values):
            self.assertAlmostEqual(actual_val, expected_val, 12)
        self.assertEqual(len(actual_values), 4)

        # inclusive end-value
        scanjob = scanjob_t({'scantype': 'scan1Dfast', 'sweepdata': {'param': 'dac1', 'range': 8, 'step': 2}})
        _, sweepvalues = scanjob._convert_scanjob_vec(station, sweeplength=5)
        actual_values = list(sweepvalues)
        expected_values = [-4.0, -2.0, 0.0, 2.0, 4.0]
        for actual_val, expected_val in zip(actual_values, expected_values):
            self.assertAlmostEqual(actual_val, expected_val, 12)
        self.assertEqual(len(actual_values), 5)

        gates.close()

    def test_convert_scanjob_vec_scan1Dfast_adjust_sweeplength(self):
        p = Parameter('p', set_cmd=None)
        gates = VirtualIVVI(
            name=qtt.measurements.scans.instrumentName('gates'), model=None)
        station = qcodes.Station(gates)
        station.gates = gates

        # inclusive end-value
        scanjob = scanjob_t({'scantype': 'scan1Dfast', 'sweepdata': {'param': p, 'start': -2, 'end': 2, 'step': .4}})
        _, sweepvalues = scanjob._convert_scanjob_vec(station, sweeplength=5)
        actual_values = list(sweepvalues)
        expected_values = [-2.0, -1.0, 0.0, 1.0, 2.0]
        self.assertEqual(expected_values, actual_values)
        self.assertEqual(len(actual_values), 5)

        gates.close()

    def test_convert_scanjob_vec_scan1Dfast_adjust_sweeplength_adjusted_end(self):
        p = Parameter('p', set_cmd=None)
        gates = VirtualIVVI(
            name=qtt.measurements.scans.instrumentName('gates'), model=None)
        station = qcodes.Station(gates)
        station.gates = gates

        # exclusive end-value
        scanjob = scanjob_t({'scantype': 'scan1Dfast',
                             'sweepdata': {'param': p, 'start': -20, 'end': 20, 'step': .0075}})
        _, sweepvalues = scanjob._convert_scanjob_vec(station)
        actual_values = list(sweepvalues)
        self.assertEqual(actual_values[0], -20.0)
        self.assertAlmostEqual(actual_values[-1], 20.0 - 0.0025, 10)
        self.assertEqual(len(actual_values), 5334)

        # inclusive end-value
        scanjob = scanjob_t({'scantype': 'scan1Dfast',
                             'sweepdata': {'param': p, 'start': -20, 'end': 20, 'step': .0075}})
        _, sweepvalues = scanjob._convert_scanjob_vec(station, sweeplength=40/.0075+1)
        actual_values = list(sweepvalues)
        self.assertEqual(actual_values[0], -20.0)
        self.assertAlmostEqual(actual_values[-1], 20.0-.0025, 10)
        self.assertAlmostEqual(scanjob['sweepdata']['end'], 20, 10)
        self.assertEqual(len(actual_values), 5334)

        # exclusive end-value
        scanjob = scanjob_t({'scantype': 'scan1Dfast',
                             'sweepdata': dict({'param': p, 'start': -500, 'end': 1,
                                                'step': .8, 'wait_time': 3e-3})})
        _, sweepvalues = scanjob._convert_scanjob_vec(station)
        actual_values = list(sweepvalues)
        self.assertEqual(actual_values[0], -500.0)
        self.assertAlmostEqual(actual_values[-1], 1 - 0.2, 10)
        self.assertAlmostEqual(scanjob['sweepdata']['end'], 1, 10)
        self.assertEqual(len(actual_values), 627)

        # inclusive end-value
        scanjob = scanjob_t({'scantype': 'scan1Dfast',
                             'sweepdata': dict({'param': p, 'start': -500, 'end': 1,
                                                'step': .8, 'wait_time': 3e-3})})
        _, sweepvalues = scanjob._convert_scanjob_vec(station, sweeplength=(501/.8) + 1)
        actual_values = list(sweepvalues)
        self.assertEqual(actual_values[0], -500.0)
        self.assertAlmostEqual(actual_values[-1], 0.8, 10)
        self.assertAlmostEqual(scanjob['sweepdata']['end'], 1, 10)
        self.assertEqual(len(actual_values), 627)

        gates.close()

    def test_convert_scanjob_vec_values_raises_exception(self):
        p = Parameter('p', set_cmd=None)
        gates = VirtualIVVI(
            name=qtt.measurements.scans.instrumentName('gates'), model=None)
        station = qcodes.Station(gates)
        station.gates = gates

        scanjob = scanjob_t({'scantype': 'scan1Dfast',
                             'sweepdata': {'param': p, 'start': 20, 'end': 20, 'step': .0075}})
        self.assertRaises(ValueError, scanjob._convert_scanjob_vec, station)
        self.assertRaises(ValueError, scanjob._convert_scanjob_vec, station, sweeplength=1)

        gates.close()

    def test_convert_scanjob_vec_range_values_will_not_raise_exception(self):
        p = Parameter('p', set_cmd=None)
        gates = VirtualIVVI(
            name=qtt.measurements.scans.instrumentName('gates'), model=None)
        station = qcodes.Station(gates)
        station.gates = gates

        idx = 1
        for idx in range(1, 5):
            for start in range(-5, 1):
                for end in range(1, 5):
                    for step_in_range in range(1, 5):
                        step = step_in_range / (idx * 10)

                        # exclusive end-value
                        scanjob = scanjob_t({'scantype': 'scan1Dfast',
                                             'sweepdata': {'param': p, 'start': start, 'end': end, 'step': step}})
                        _ = scanjob._convert_scanjob_vec(station)

                        scanjob = scanjob_t({'scantype': 'scan1Dfast',
                                             'sweepdata': {'param': p, 'start': start, 'end': end, 'step': step}})

                        # inclusive end-value
                        scanjob = scanjob_t({'scantype': 'scan1Dfast',
                                             'sweepdata': {'param': p, 'start': start, 'end': end, 'step': step}})
                        # generate a sweeplength so that the step-value doesn't change
                        _ = scanjob._convert_scanjob_vec(station, sweeplength=((end-start)/step) + 1)
                        scanjob = scanjob_t({'scantype': 'scan1Dfast',
                                             'sweepdata': {'param': p, 'start': start, 'end': end, 'step': step}})

        # all the conversions were successful
        self.assertEqual(idx, 4)
        gates.close()

    def test_convert_scanjob_vec_scan2Dfast(self):
        p = Parameter('p', set_cmd=None)
        q = Parameter('q', set_cmd=None)
        r = ScaledParameter(p, division=4)
        _ = MultiParameter(instrumentName('multi_param'), [p, q])

        gates = VirtualIVVI(
            name=qtt.measurements.scans.instrumentName('gates'), model=None)
        station = qcodes.Station(gates)
        station.gates = gates

        scanjob = scanjob_t({'scantype': 'scan2Dfast',
                             'sweepdata': dict(
                                 {'param': p, 'start': 0, 'end': 10, 'step': 4}), 'minstrument': [r]})

        scanjob['stepdata'] = dict(
            {'param': q, 'start': 24, 'end': 32, 'step': 1.})
        stepvalues, sweepvalues = scanjob._convert_scanjob_vec(station, 3, 5)
        actual_stepvalues = list(stepvalues)
        expected_stepvalues = [24.0, 28.0, 32.0]
        self.assertEqual(expected_stepvalues, actual_stepvalues)
        self.assertEqual(len(actual_stepvalues), 3)

        actual_sweepvalues = list(sweepvalues)
        expected_sweepvalues = [0, 2.5, 5.0, 7.5, 10.0]
        self.assertEqual(expected_sweepvalues, actual_sweepvalues)
        self.assertEqual(len(actual_sweepvalues), 5)
        gates.close()

    def test_convert_scanjob_vec_regression(self):
        station = qcodes.Station()
        ivvi = VirtualIVVI(name='ivvi', model=None)
        gates = qtt.instrument_drivers.gates.VirtualDAC(
            'gates', instruments=[ivvi], gate_map={'P1': (0, 1), 'P2': (0, 2)})
        station.add_component(gates)
        num = 566
        scanjob = scanjob_t({'minstrument': [1], 'minstrumenthandle': ('m4i', [1]), 'wait_time_startscan': 0.04, 'stepdata': {'wait_time': 0.2}, 'Naverage': 2000, 'sweepdata': {
                            'period': 0.0005, 'param': 'P1', 'range': -5, 'step': -0.01098901098901099, 'start': 714.84130859375, 'end': 709.84130859375}, 'scantype': 'scan1Dfast'})
        _, s = scanjob._convert_scanjob_vec(station=station, sweeplength=num)
        self.assertEqual(len(s), num)

        gates.close()
        ivvi.close()
