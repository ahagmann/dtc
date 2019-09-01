#
# Copyright (C) 2019 https://github.com/ahagmann
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#

import matplotlib
import matplotlib.pyplot as plt
import numpy as np


class Timing:
    def __init__(self,
                period,
                setup,
                hold,
                source_setup_margin,
                source_hold_margin,
                sink_setup_margin,
                sink_hold_margin):

        self.period = period
        self.setup = setup
        self.hold = hold
        self.source_setup_margin = source_setup_margin
        self.source_hold_margin = source_hold_margin
        self.sink_setup_margin = sink_setup_margin
        self.sink_hold_margin = sink_hold_margin

        self._calc()

    def _calc(self):
        self.source_setup = self.setup + self.source_setup_margin
        self.source_hold = self.hold + self.source_hold_margin
        self.sink_setup = self.setup - self.sink_setup_margin
        self.sink_hold = self.hold - self.sink_hold_margin

        self.source_min_output_delay = -self.source_hold
        self.source_max_output_delay = self.source_setup
        self.sink_min_input_delay = self.sink_hold
        self.sink_max_input_delay = self.period - self.sink_setup

        self.overall_setup_margin = self.source_setup - self.sink_setup
        self.overall_hold_margin = self.source_hold - self.sink_hold

        if self.overall_setup_margin < 0:
            print("WARNING: overall setup margin <0")

        if self.overall_hold_margin < 0:
            print("WARNING: overall hold margin <0")

        # todo: how to model signals back from sink to source?

    def plot(self):
        Plot().show(self.period,
                    self.setup,
                    self.hold,
                    self.source_setup,
                    self.source_hold,
                    self.sink_setup,
                    self.sink_hold,
                    self.source_min_output_delay,
                    self.source_max_output_delay,
                    self.sink_min_input_delay,
                    self.sink_max_input_delay,
                    self.overall_setup_margin,
                    self.overall_hold_margin)

    def print_source_constraints(self):
        print("# output delay min: %g" % self.source_min_output_delay)
        print("# output delay max: %g" % self.source_max_output_delay)

        print("set t_SU {}".format(self.setup))
        print("set t_HO {}".format(self.hold))
        print("set t_SU_margin {}".format(self.source_setup_margin))
        print("set t_HO_margin {}".format(self.source_hold_margin))
        print("set t_SU_value [expr t_SU + t_SU_margin]")
        print("set t_HO_value [expr t_HO + t_HO_margin]")
        print("set_output_delay -clock <CLK_OUT> -min [get_ports <DATA>] [expr -$t_HO_value]")
        print("set_output_delay -clock <CLK_OUT> -max -add_delay [get_ports <DATA>] $t_SU_value")

    def print_sink_constraints(self):
        print("# input delay min: %g" % self.sink_min_input_delay)
        print("# input delay max: %g" % self.sink_max_input_delay)

        print("set t_SU {}".format(self.setup))
        print("set t_HO {}".format(self.hold))
        print("set period {}".format(self.period))
        print("set t_SU_margin {}".format(self.sink_setup_margin))
        print("set t_HO_margin {}".format(self.sink_hold_margin))
        print("set t_SU_value [expr t_SU - t_SU_margin]")
        print("set t_HO_value [expr t_HO - t_HO_margin]")
        print("set_input_delay -clock <CLK> -min [get_ports <DATA>] $t_HO_value")
        print("set_input_delay -clock <CLK> -max -add_delay [get_ports <DATA>] [expr $period - $t_SU_value]")


class Plot():
    def _clock_signal(self, time, period, offset=0):
        values = []
        for t in time:
            if t % period < period / 2:
                v = 1
            else:
                v = 0
            values.append(v)
        return np.array(values) + offset

    def _data_signal(self, time, old_end, new_start, slope_duration=0.5, offset=0):
        values = []
        for t in time:
            if t < old_end - slope_duration:
                v = 0
            elif t < old_end + slope_duration:
                v = 1.0/slope_duration/2.0 * (t - old_end) + 0.5
            elif t < new_start - slope_duration:
                v = 1
            elif t < new_start + slope_duration:
                v = -1.0/slope_duration/2.0 * (t - new_start) + 0.5
            else:
                v = 0
            values.append(v)
        return np.array(values) + offset, 1 - np.array(values) + offset

    def _annotated_arrow(self, ax, x1, x2, offset, text, padding, text_begin=False):
        ax.annotate("", xy=(x2, offset - 0.5), xytext=(x1, offset - 0.5), arrowprops=dict(arrowstyle="-|>", connectionstyle="arc3"))
        if text_begin:
            textx = x1
            if x1 < x2:
                ha = 'right'
                padding = -padding
            else:
                ha = 'left'
        else:
            textx = x2
            if x1 < x2:
                ha = 'left'
            else:
                ha = 'right'
                padding = -padding
        ax.annotate(text, xy=(textx + padding, offset - 0.5), ha=ha, va='center')

    def show(self,
             period,
             setup,
             hold,
             source_setup,
             source_hold,
             sink_setup,
             sink_hold,
             source_min_output_delay,
             source_max_output_delay,
             sink_min_input_delay,
             sink_max_input_delay,
             margin_setup,
             margin_hold):
        begin = -max(source_setup, sink_setup, period*0.1)*1.1
        end = max(source_hold, sink_hold, period*0.1)*1.1 + period
        clock_offset = 6.5
        source_offset = 4.5
        sink_offset = 2

        t = np.arange(begin, end, period/1000.0)
        clock = self._clock_signal(t, period, clock_offset)
        data_source, data_source_n = self._data_signal(t, 0 + source_hold, period - source_setup, period*0.01, offset=source_offset)
        data_sink, data_sink_n = self._data_signal(t, 0 + sink_hold, period - sink_setup, period*0.01, offset=sink_offset)

        fig, ax = plt.subplots(figsize=(14,5))
        ax.plot(t, clock, color='black')
        ax.plot(t, data_source, color='black')
        ax.plot(t, data_source_n, color='black')
        ax.plot(t, data_sink, color='black')
        ax.plot(t, data_sink_n, color='black')

        ax.text(0 - period/100.0, sink_offset + 0.5, "Sink\nOld Data", ha="right", va="center", size=15)
        ax.text(0 - period/100.0, source_offset + 0.5, "Source\nOld Data", ha="right", va="center", size=15)
        ax.text(period + period/100.0, sink_offset + 0.5, "Sink\nNew Data", ha="left", va="center", size=15)
        ax.text(period + period/100.0, source_offset + 0.5, "Source\nNew Data", ha="left", va="center", size=15)

        ax.axvline(x=0, linewidth=0.5, color='black')
        ax.axvline(x=source_hold, linewidth=0.5, color='black')
        ax.axvline(x=sink_hold, linewidth=0.5, color='black')
        ax.axvline(x=period - source_setup, linewidth=0.5, color='black')
        ax.axvline(x=period - sink_setup, linewidth=0.5, color='black')
        ax.axvline(x=period, linewidth=0.5, color='black')

        self._annotated_arrow(ax, sink_hold, source_hold, clock_offset - 0, "$margin_{HO}=%g$" % margin_hold, period/100.0, True)
        self._annotated_arrow(ax, period - sink_setup, period - source_setup, clock_offset - 0, "$margin_{SU}=%g$" % margin_setup, period/100.0, True)

        self._annotated_arrow(ax, 0, source_hold, source_offset, "$t_{HO}=%g$" % source_hold, period/100.0, True)
        self._annotated_arrow(ax, period, period - source_setup, source_offset, "$t_{SU}=%g$" % source_setup, period/100.0, True)
        self._annotated_arrow(ax, 0, sink_hold, sink_offset, "$t_{HO}=%g$" % sink_hold, period/100.0, True)
        self._annotated_arrow(ax, period, period - sink_setup, sink_offset, "$t_{SU}=%g$" % sink_setup, period/100.0, True)

        self._annotated_arrow(ax, source_hold, 0, source_offset - 0.5, "$out_{min}=%g$" % source_min_output_delay, period/100.0, False)
        self._annotated_arrow(ax, period, period - source_max_output_delay, source_offset - 0.5, "$out_{max}=%g$" % source_max_output_delay, period/100.0, True)
        self._annotated_arrow(ax, 0, sink_hold, sink_offset - 0.5, "$in_{min}=%g$" % sink_min_input_delay, period/100.0, True)
        self._annotated_arrow(ax, 0, sink_max_input_delay, sink_offset - 1, "$in_{max}=%g$" % sink_max_input_delay, period/100.0, True)

        ax.axvspan(0 - setup, hold, alpha=0.2, color='green')
        ax.axvspan(hold, source_hold, alpha=0.2, color='grey')
        ax.axvspan(period - setup, period + hold, alpha=0.2, color='green')
        ax.axvspan(period - source_setup, period - setup, alpha=0.2, color='grey')

        leg = ax.legend(loc='lower right', bbox_to_anchor=(1.2, 0.9), handles=[
            matplotlib.patches.Patch(color='green', alpha=0.2, label='Setup/Hold Area'),
            matplotlib.patches.Patch(color='grey', alpha=0.2, label='Source Margin')])

        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_visible(False)
        ax.spines['top'].set_visible(False)
        ax.axes.get_yaxis().set_visible(False)
        ax.set_ylim(ymin=0)

        plt.show()
