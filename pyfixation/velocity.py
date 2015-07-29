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

from scipy.signal import savgol_coeffs
from scipy.ndimage import convolve1d

import numpy as np
import math
from exceptions import ValueError
import os

class VelocityProcessor(object):

	def __init__(self, resolutionX, resolutionY, screenWidth, screenHeight, samplerate, minsac):
		self.resolutionX = resolutionX
		self.resolutionY = resolutionY
		self.centerx = self.resolutionX / 2.0
		self.centery = self.resolutionY / 2.0
		self.screenWidth = screenWidth
		self.screenHeight = screenHeight
		self.samplerate = samplerate
		self.order = 2
		self.ts = 1.0/self.samplerate
		self.window = int(2 * int(minsac/self.ts) + 3)
		self.halfwindow = int(self.window/2)
		self.coeff = [savgol_coeffs(self.window, self.order, 0), savgol_coeffs(self.window, self.order, 1), savgol_coeffs(self.window, self.order, 2)]
		self.time = np.zeros(self.window, dtype = float)
		self.winax = np.zeros(self.window, dtype = float)
		self.winay = np.zeros(self.window, dtype = float)
		self.winx = np.zeros(self.window, dtype = float)
		self.winy = np.zeros(self.window, dtype = float)

	def appendWindow(self, t, ax, ay, x, y):
		self.time = np.append(self.time[1:], t)
		self.winax = np.append(self.winax[1:], ax)
		self.winay = np.append(self.winay[1:], ay)
		self.winx = np.append(self.winx[1:], x)
		self.winy = np.append(self.winy[1:], y)

	def processWindow(self):
		t = self.time[self.halfwindow]
		x = convolve1d(self.winx, self.coeff[0])[self.halfwindow]
		y = convolve1d(self.winy, self.coeff[0])[self.halfwindow]
		vx = convolve1d(self.winax, self.coeff[1])[self.halfwindow]
		vy = convolve1d(self.winay, self.coeff[1])[self.halfwindow]
		ax = convolve1d(self.winax, self.coeff[2])[self.halfwindow]
		ay = convolve1d(self.winay, self.coeff[2])[self.halfwindow]
		v = 1.0 * self.samplerate * math.sqrt(vx ** 2 + vy ** 2)
		a = 1.0 * self.samplerate * math.sqrt(ax ** 2 + ay ** 2)
		return t, x, y, v, a

	def distance2point(self, x, y, rx, ry, sw, sh, ez, ex, ey):
		dx = x / rx * sw - sw / 2.0 + ex
		dy = y / ry * sh - sh / 2.0 - ey
		return math.sqrt(ez ** 2 + dx ** 2 + dy ** 2)

	def subtendedAngle(self, x1, y1, x2, y2, rx, ry, sw, sh, ez, ex, ey):
		d1 = self.distance2point(x1, y1, rx, ry, sw, sh, ez, ex, ey)
		d2 = self.distance2point(x2, y2, rx, ry, sw, sh, ez, ex, ey)
		dX = sw*((x2-x1)/rx)
		dY = sh*((y2-y1)/ry)
		dS = math.sqrt(dX ** 2 + dY ** 2)
		w1 = d1 ** 2 + d2 ** 2 - dS ** 2
		w2 = 2 * d1 * d2
		return math.acos(min(max(w1/w2,-1.0),1.0)) * 180.0/math.pi

	def processData( self, t, x, y, ez, ex=0, ey=0):
		ax = self.subtendedAngle(x, self.centery, self.centerx, self.centery, self.resolutionX, self.resolutionY, self.screenWidth, self.screenHeight, ez, ex, ey)
		ay = self.subtendedAngle(self.centerx, y, self.centerx, self.centery, self.resolutionX, self.resolutionY, self.screenWidth, self.screenHeight, ez, ex, ey)
		self.appendWindow(t, ax, ay, x, y)
		return self.processWindow()

if __name__ == '__main__':
	from twisted.internet import reactor
	from twisted.internet.task import LoopingCall
	from pyviewx.client import iViewXClient, Dispatcher
	from pyviewx.pygame import Calibrator

	import pygame
	import random

	pygame.display.init()
	pygame.font.init()

	screen = pygame.display.set_mode( ( 0, 0 ), pygame.FULLSCREEN )
	screen_rect = screen.get_rect()

	f = pygame.font.Font( None, 16 )

	angle1 = random.uniform( 0, 360 )
	angle2 = random.uniform( 0, 360 )

	velThreshold = 75
	nFixations = 0
	fixating = False

	gaze = None

	d = Dispatcher()

	@d.listen('ET_SPL')
	def iViewXEvent(inResponse):
		global gaze, fix, samp, fp, winx, winy, aw, velThreshold, nFixations, fixating
		t = float(inResponse[0])
		x = float(inResponse[2])
		y = float(inResponse[4])
		ex = float(inResponse[10])
		ey = float(inResponse[12])
		ez = float(inResponse[14])

		t, x, y, v, a = fp.processData(t, x, y, ez, ex, ey)
		if x != None and y != None and v < velThreshold:
			if not fixating:
				nFixations += 1
				fixating = True
			gaze = (int(x),int(y))
		else:
			fixating = False
			gaze = None

	def draw_text( text, font, color, loc, surf ):
		t = font.render( text, True, color )
		tr = t.get_rect()
		tr.center = loc
		surf.blit( t, tr )
		return tr

	def update():
		global angle1, angle2, gaze, fp, velThreshold
		if state < 0:
			return
		for event in pygame.event.get():
			if event.type == pygame.KEYUP:
				if event.key == pygame.K_UP:
					velThreshold += 0.5
				elif event.key == pygame.K_DOWN:
					velThreshold -= 0.5
				elif event.key == pygame.K_ESCAPE:
					cleanup()
		screen.fill( ( 0, 0, 0 ) )
		pygame.draw.circle( screen, ( 0, 0, 255 ), screen_rect.center, 10, 0 )
		pygame.draw.circle( screen, ( 0, 0, 255 ), ( screen_rect.width / 10, screen_rect.height / 10 ), 10, 0 )
		pygame.draw.circle( screen, ( 0, 0, 255 ), ( screen_rect.width / 10, screen_rect.height / 10 * 9 ), 10, 0 )
		pygame.draw.circle( screen, ( 0, 0, 255 ), ( screen_rect.width / 10 * 9, screen_rect.height / 10 ), 10, 0 )
		pygame.draw.circle( screen, ( 0, 0, 255 ), ( screen_rect.width / 10 * 9, screen_rect.height / 10 * 9 ), 10, 0 )
		pygame.draw.circle( screen, ( 0, 0, 255 ), ( screen_rect.width / 5, screen_rect.height / 5 ), 10, 0 )
		pygame.draw.circle( screen, ( 0, 0, 255 ), ( screen_rect.width / 5, screen_rect.height / 5 * 4 ), 10, 0 )
		pygame.draw.circle( screen, ( 0, 0, 255 ), ( screen_rect.width / 5 * 4, screen_rect.height / 5 ), 10, 0 )
		pygame.draw.circle( screen, ( 0, 0, 255 ), ( screen_rect.width / 5 * 4, screen_rect.height / 5 * 4 ), 10, 0 )
		pygame.draw.circle( screen, ( 0, 0, 255 ), ( screen_rect.centerx + int( math.cos( angle1 ) * screen_rect.height / 6 ), screen_rect.centery + int( math.sin( angle1 ) * screen_rect.height / 6 ) ), 5, 0 )
		pygame.draw.circle( screen, ( 0, 0, 255 ), ( screen_rect.centerx + int( math.cos( angle2 ) * screen_rect.height / 3 ), screen_rect.centery + int( math.sin( angle2 ) * screen_rect.height / 3 ) ), 5, 0 )
		if gaze!=None:
			pygame.draw.circle( screen, ( 255, 255, 0 ), gaze, 3, 1 )
		draw_text( "%d" % velThreshold, f, ( 255, 255, 255 ), ( screen_rect.left + 50, screen_rect.bottom - 15 ), screen )
		draw_text( "%d" % nFixations, f, ( 255, 255, 255 ), ( screen_rect.left + 50, screen_rect.top + 15 ), screen )
		pygame.display.flip()

		angle1 += .05
		if angle1 >= 360:
			angle1 = 0

		angle2 -= .025
		if angle2 <= 0:
			angle2 = 360

	def cleanup( *args, **kwargs ):
		reactor.stop()

	def start( lc, results ):
		global state, update, client, cleanup
		state = 0
		client.addDispatcher( d )
		lc = LoopingCall( update )
		dd = lc.start( 1.0 / 30 )
		dd.addCallbacks( cleanup )

	client = iViewXClient( os.environ['EYE_TRACKER'], 4444 )
	reactor.listenUDP( 5555, client )
	calibrator = Calibrator( client, screen, reactor = reactor, eye = 0 )
	fp = VelocityProcessor(1680,1050,473.76,296.1,500,.03)
	calibrator.start(start)
	reactor.run()
