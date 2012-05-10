# -*- coding:    utf-8 -*-
#===============================================================================
# This file is part of PyFixation.
# Copyright (C) 2012 Ryan Hope <rmh3093@gmail.com>
#
# PyViewX is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyViewX is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PyViewX.  If not, see <http://www.gnu.org/licenses/>.
#===============================================================================

from __future__ import division
import math, copy

class FixationData( object ):
    """NEW,PRES,PREV FIXATION DATA"""

    start_count = 0
    end_count = 0
    n_samples = 0
    sum_x = 0.0
    sum_y = 0.0
    fX = 0.0
    fY = 0.0

class GazeData( object ):
    """RING BUFFER DATA"""

    gaze_x = 0.0
    gaze_y = 0.0
    gaze_found = 0
    eye_motion_state = 0
    fix_x = -0.0
    fix_y = -0.0
    gaze_deviation = -0.1
    sac_duration = 0
    fix_duration = 0

class DispersionFP( object ):
    """Eye Fixation Analysis Functions"""

    MOVING = 0
    FIXATING = 1
    FIXATION_COMPLETED = 2

    NEW_FIX = 0
    PRES_FIX = 1
    PREV_FIX = 2

    def updateSettings( self ):
        self.max_missed_samples = int( math.ceil( 0.05 * self.sample_rate ) )
        self.max_out_samples = int( math.ceil( 0.15 * self.sample_rate ) )
        self.min_fix_samples = int( math.ceil( self.min_fixation_ms * self.sample_rate / 1000.0 ) )
        if self.min_fix_samples < self.max_out_samples:
            self.min_fix_samples = self.max_out_samples
        self.RING_SIZE = self.sample_rate + 1

    def __init__( self, px_per_mm, sample_rate = 120, min_fixation_ms = 100,
                 gaze_deviation_thresh_mm = 6.35 ):
        super( DispersionFP, self ).__init__()

        self.gaze_deviation_thresh_px = gaze_deviation_thresh_mm * px_per_mm
        self.sample_rate = sample_rate
        self.min_fixation_ms = min_fixation_ms

        self.updateSettings()

        self.ring_buffer = [GazeData() for _ in range( 0, self.RING_SIZE )]
        self.ring_index = 0
        self.ring_index_delay = 0#self.RING_SIZE - self.min_fix_samples

        self.call_count = 0
        self.fixations = [FixationData() for _ in range( 0, 3 )]

        self.samples_since_last_good = 0
        self.out_samples = 0
        self.pres_dv = 0
        self.new_dv = 0

        self._reset_fix( self.PRES_FIX )
        self._reset_fix( self.NEW_FIX )

    def _calc_deviation( self, fix_type, gaze_x, gaze_y ):
        """This function calculates the deviation of the gazepoint from the
        argument fix_type fixation location."""

        fdx = gaze_x - self.fixations[fix_type].fX
        fdy = gaze_y - self.fixations[fix_type].fY

        dvsq = fdx * fdx + fdy * fdy

        assert ( dvsq >= 0.0 )
        if dvsq < 0.0:
            dvsq = 0.0
        fdv = math.sqrt( dvsq )

        if fix_type == self.PRES_FIX:
            assert ( self.ring_index >= 0 and self.ring_index < self.RING_SIZE )
            self.ring_buffer[self.ring_index].gaze_deviation = fdv

        return fdv

    def _reset_fix( self, fix_type ):
        """This function resets the argument fix_type fixation,
        i.e. declares it nonexistent."""

        self.fixations[fix_type].start_count = 0
        self.fixations[fix_type].end_count = 0
        self.fixations[fix_type].n_samples = 0
        self.fixations[fix_type].sum_x = 0.0
        self.fixations[fix_type].sum_y = 0.0
        self.fixations[fix_type].fX = 0.0
        self.fixations[fix_type].fY = 0.0

        if fix_type == self.PRES_FIX:
            self.out_samples = 0

    def _start_fix( self, fix_type, gaze_x, gaze_y ):
        """This function starts the argument fix_type fixation at the argument
        gazepoint and makes sure there is no new fixation hypothesis."""

        self.fixations[fix_type].n_samples = 1
        self.fixations[fix_type].sum_x = gaze_x
        self.fixations[fix_type].sum_y = gaze_y
        self.fixations[fix_type].fX = gaze_x
        self.fixations[fix_type].fY = gaze_y
        self.fixations[fix_type].start_count = self.call_count
        self.fixations[fix_type].end_count = self.call_count

        if fix_type == self.PRES_FIX:
            self.out_samples = 0
            self._reset_fix( self.NEW_FIX )

    def _check_if_fixating( self ):
        """This function checks to see whether there are enough samples in the
        PRESENT fixation to declare that the eye is fixating yet, and if there
        is a true fixation going on, it updates the ring buffers to reflect
        the fixation."""

        if self.fixations[self.PRES_FIX].n_samples >= self.min_fix_samples:
            for i in range( 0, self.min_fix_samples ):
                j = self.ring_index - i
                if j < 0:
                    j += self.RING_SIZE

                assert( j >= 0 and j < self.RING_SIZE )

                self.ring_buffer[j].eye_motion_state = self.FIXATING
                self.ring_buffer[j].fix_x = self.fixations[self.PRES_FIX].fX
                self.ring_buffer[j].fix_y = self.fixations[self.PRES_FIX].fY

                self.ring_buffer[j].sac_duration = \
                    self.fixations[self.PRES_FIX].start_count - \
                    self.fixations[self.PREV_FIX].end_count - 1
                self.ring_buffer[j].fix_duration = \
                    self.fixations[self.PRES_FIX].end_count - \
                    i - self.fixations[self.PRES_FIX].start_count + 1

    def _update_fix( self, fix_type, gaze_x, gaze_y ):
        """This function updates the argument fix_type fixation with the
        argument gazepoint, checks if there are enough samples to declare that
        the eye is now fixating, and makes sure there is no hypothesis for a
        new fixation."""

        self.fixations[fix_type].n_samples += 1
        self.fixations[fix_type].sum_x += gaze_x
        self.fixations[fix_type].sum_y += gaze_y
        self.fixations[fix_type].fX = self.fixations[fix_type].sum_x / \
            self.fixations[fix_type].n_samples
        self.fixations[fix_type].fY = self.fixations[fix_type].sum_y / \
            self.fixations[fix_type].n_samples
        self.fixations[fix_type].end_count = self.call_count

        if fix_type == self.PRES_FIX:
            self.out_samples = 0
            self._check_if_fixating()
            self._reset_fix( self.NEW_FIX )

    def _move_new_to_pres( self ):
        """This function copies the new fixation data into the present
        fixation, and resets the new fixation."""

        self.out_samples = 0

        self.fixations[self.PRES_FIX] = copy.copy( self.fixations[self.NEW_FIX] )

        self._reset_fix( self.NEW_FIX )

        self._check_if_fixating()

    def _declare_completed( self ):
        """This function:
        a) declares the present fixation to be completed,
        b) moves the present fixation to the prior fixation, and
        c) moves the new fixation, if any, to the present fixation."""

        ring_index_completed = self.ring_index - \
            self.samples_since_last_good
        if ring_index_completed < 0:
            ring_index_completed += self.RING_SIZE

        self.ring_buffer[ring_index_completed].eye_motion_state = \
            self.FIXATION_COMPLETED

        self.fixations[self.PREV_FIX] = copy.copy( self.fixations[self.PRES_FIX] )

        self._move_new_to_pres()

    def _restore_out_points( self ):
        """This function restores any previous gazepoints that were left out of
        the fixation and are now known to be part of the present fixation."""

        if self.samples_since_last_good > 1:

            for i in range( 1, self.samples_since_last_good ):
                j = self.ring_index - i
                if j < 0:
                    j += self.RING_SIZE

                assert ( j >= 0 and j < self.RING_SIZE )

                if self.ring_buffer[j].gaze_found:
                    self.fixations[self.PRES_FIX].n_samples += 1
                    self.fixations[self.PRES_FIX].sum_x += \
                        self.ring_buffer[j].gaze_x
                    self.fixations[self.PRES_FIX].sum_y += \
                        self.ring_buffer[j].gaze_y
                    self.ring_buffer[j].eye_motion_state = self.FIXATING

            self.out_samples = 0

    def detect_fixation( self, gaze_found, gaze_x, gaze_y ):
        """This function converts a series of uniformly-sampled (raw) gaze
        points into a series of variable-duration saccades and fixations."""

        self.call_count += 1
        self.ring_index += 1
        if self.ring_index >= self.RING_SIZE:
            self.ring_index = 0
        self.ring_index_delay = self.ring_index - self.min_fix_samples
        if self.ring_index_delay < 0:
            self.ring_index_delay += self.RING_SIZE

        assert ( self.ring_index >= 0 and self.ring_index < self.RING_SIZE )
        assert ( self.ring_index_delay >= 0 and
                self.ring_index_delay < self.RING_SIZE )

        self.ring_buffer[self.ring_index].gaze_x = gaze_x
        self.ring_buffer[self.ring_index].gaze_y = gaze_y
        self.ring_buffer[self.ring_index].gaze_found = gaze_found

        self.ring_buffer[self.ring_index].eye_motion_state = self.MOVING
        self.ring_buffer[self.ring_index].fix_x = -0.0
        self.ring_buffer[self.ring_index].fix_y = -0.0
        self.ring_buffer[self.ring_index].gaze_deviation = -0.1
        self.ring_buffer[self.ring_index].sac_duration = 0
        self.ring_buffer[self.ring_index].fix_duration = 0

        if self.fixations[self.PRES_FIX].end_count > 0:
            self.samples_since_last_good = self.call_count - \
                self.fixations[self.PRES_FIX].end_count
        else:
            self.samples_since_last_good = 1

        if gaze_found:
            if self.fixations[self.PRES_FIX].n_samples > 0:
                self.pres_dv = self._calc_deviation( self.PRES_FIX,
                                                   gaze_x, gaze_y )
                if self.pres_dv <= self.gaze_deviation_thresh_px:
                    self._restore_out_points()
                    self._update_fix( self.PRES_FIX, gaze_x, gaze_y )
                else:
                    self.out_samples += 1
                    if self.out_samples <= self.max_out_samples:
                        if self.fixations[self.NEW_FIX].n_samples > 0:
                            self.new_dv = self._calc_deviation( self.NEW_FIX,
                                                              gaze_x, gaze_y )
                            if self.new_dv <= self.gaze_deviation_thresh_px:
                                self._update_fix( self.NEW_FIX, gaze_x, gaze_y )
                            else:
                                self._start_fix( self.NEW_FIX, gaze_x, gaze_y )
                        else:
                            self._start_fix( self.NEW_FIX, gaze_x, gaze_y )
                    else:
                        if self.fixations[self.PRES_FIX].n_samples >= \
                            self.min_fix_samples:
                            self._declare_completed()
                        else:
                            self._move_new_to_pres()
                        if self.fixations[self.PRES_FIX].n_samples > 0:
                            self.pres_dv = self._calc_deviation( self.PRES_FIX,
                                                               gaze_x, gaze_y )
                            if self.pres_dv <= self.gaze_deviation_thresh_px:
                                self._update_fix( self.PRES_FIX, gaze_x, gaze_y )
                            else:
                                self._start_fix( self.NEW_FIX, gaze_x, gaze_y )
                        else:
                            self._start_fix( self.PRES_FIX, gaze_x, gaze_y )
            else:
                self._start_fix( self.PRES_FIX, gaze_x, gaze_y )
        else:
            if self.samples_since_last_good <= self.max_missed_samples:
                pass
            else:
                if self.fixations[self.PRES_FIX].n_samples >= \
                    self.min_fix_samples:
                    self._declare_completed()
                else:
                    self._move_new_to_pres()

        assert ( self.ring_index_delay >= 0 and
                self.ring_index_delay < self.RING_SIZE )

        return self.ring_buffer[self.ring_index_delay]
