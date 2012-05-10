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

import savitzky_golay as sg
import numpy as np
import math
from exceptions import ValueError

class VelocityFP( object ):

	def __init__( self, resolutionX = 1680, resolutionY = 1050, screenWidth = 473.8, screenHeight = 296.1, accThreshold = 7, velThreshold = 40, blinkThreshold = 400, minFix = 40, samplerate = 500 ):
		self.resolutionX = resolutionX
		self.resolutionY = resolutionY
		self.centerx = self.resolutionX / 2.0
		self.centery = self.resolutionY / 2.0
		self.screenWidth = screenWidth
		self.screenHeight = screenHeight
		self.velThreshold = velThreshold
		self.accThreshold = accThreshold
		self.blinkThreshold = blinkThreshold
		self.minFix = minFix
		self.samplerate = samplerate
		self.minSamples = int( self.minFix / ( 1.0 / self.samplerate * 1000.0 ) )
		self.fix = None
		self.fixsamples = [0, None, None]

		self.coeff = [sg.calc_coeff( 11, 2, 0 ), sg.calc_coeff( 11, 2, 1 ), sg.calc_coeff( 11, 2, 2 )]

		self.time = np.zeros( 11, dtype = float )
		self.winax = np.zeros( 11, dtype = float )
		self.winay = np.zeros( 11, dtype = float )
		self.winx = np.zeros( 11, dtype = float )
		self.winy = np.zeros( 11, dtype = float )
		self.d = None
		self.maxv = 0
		self.output = open( "velocity.txt", "w" )

	def degrees2pixels( self, a, d, resolutionX, resolutionY, screenWidth, screenHeight ):
		a = a * math.pi / 180
		w = 2 * math.tan( a / 2 ) * d
		aiph = resolutionX * w / screenWidth
		aipv = resolutionY * w / screenHeight
		return aiph, aipv

	def appendWindow( self, t, ax, ay, x, y ):
		self.time = np.append( self.time[1:], t )
		self.winax = np.append( self.winax[1:], ax )
		self.winay = np.append( self.winay[1:], ay )
		self.winx = np.append( self.winx[1:], x )
		self.winy = np.append( self.winy[1:], y )

	def processWindow( self ):
		x = sg.filter( self.winx, self.coeff[0] )[6]
		y = sg.filter( self.winy, self.coeff[0] )[6]
		vx = sg.filter( self.winax, self.coeff[1] )[6]
		vy = sg.filter( self.winay, self.coeff[1] )[6]
		ax = sg.filter( self.winax, self.coeff[2] )[6]
		ay = sg.filter( self.winay, self.coeff[2] )[6]
		v = 500.0 * math.sqrt( vx ** 2 + vy ** 2 )
		a = 500.0 * math.sqrt( ax ** 2 + ay ** 2 )
		return self.time[6], v, a, x, y

	def distance2point( self, x, y, vx, vy, vz, rx, ry, sw, sh ):
		dx = x / rx * sw - rx / 2.0 + vx
		dy = y / ry * sh - ry / 2.0 - vy
		sd = math.sqrt( dx ** 2 + dy ** 2 )
		return math.sqrt( vz ** 2 + sd ** 2 )

	def subtendedAngle( self, x1, y1, x2, y2, vx, vy, vz, rx, ry, sw, sh ):
		d1 = self.distance2point( x1, y1, vx, vy, vz, rx, ry, sw, sh )
		d2 = self.distance2point( x2, y2, vx, vy, vz, rx, ry, sw, sh )
		dX = sw * ( ( x2 - x1 ) / rx )
		dY = sh * ( ( y2 - y1 ) / ry )
		dS = math.sqrt( dX ** 2 + dY ** 2 )
		rad = math.acos( max( min( ( d1 ** 2 + d2 ** 2 - dS ** 2 ) / ( 2 * d1 * d2 ), 1 ), -1 ) )
		return ( rad / ( 2 * math.pi ) ) * 360

	def processData( self, t, d, x, y, ex, ey, ez ):
		if not d:
			self.fixsamples = [0, None, None]
			return None, None
		ax = self.subtendedAngle( x, self.centery, self.centerx, self.centery, ex, ey, ez, self.resolutionX, self.resolutionY, self.screenWidth, self.screenHeight )
		ay = self.subtendedAngle( self.centerx, y, self.centerx, self.centery, ex, ey, ez, self.resolutionX, self.resolutionY, self.screenWidth, self.screenHeight )
		self.appendWindow( t, ax, ay, x, y )
		t, v, a, x, y = self.processWindow()
		if v > self.maxv:
			self.maxv = v
		self.output.write( "%.4f\t%.2f\t%.2f\n" % ( t, v, a ) )
		if np.isnan( v ):
			self.fixsamples = [0, None, None]
			return None, None
		else:
			if a < self.accThreshold:#not ( a > self.accThreshold or v > self.velThreshold ):
				ncount = self.fixsamples[0] + 1
				if self.fixsamples[1] == None:
					self.fixsamples[1] = x
				else:
					self.fixsamples[1] = ( self.fixsamples[0] * self.fixsamples[1] + x ) / ncount
				if self.fixsamples[2] == None:
					self.fixsamples[2] = y
				else:
					self.fixsamples[2] = ( self.fixsamples[0] * self.fixsamples[2] + y ) / ncount
				self.fixsamples[0] = ncount
				if self.fixsamples[0] >= self.minSamples:
					return ( self.fixsamples[1], self.fixsamples[2] ), self.fixsamples[0]
				else:
					return None, None
			else:
				self.fixsamples = [0, None, None]
				return None, None


if __name__ == '__main__':
	from twisted.internet import reactor
	from twisted.internet.task import LoopingCall
	from pyviewx import iViewXClient, Dispatcher
	from pyviewx.pygamesupport import Calibrator

	import pygame
	import random

	pygame.display.init()
	pygame.font.init()

	state = -1

	#screen = pygame.display.set_mode( ( 1024, 768 ), 0 )
	screen = pygame.display.set_mode( ( 0, 0 ), pygame.FULLSCREEN )
	screen_rect = screen.get_rect()

	f = pygame.font.Font( None, 16 )

	angle1 = random.uniform( 0, 360 )
	angle2 = random.uniform( 0, 360 )

	gaze = None
	fix = None
	samp = None
	startTime = None

	d = Dispatcher()

	@d.listen( 'ET_SPL' )
	def iViewXEvent( inSender, inEvent, inResponse ):
		global gaze, fix, samp, fp, startTime
		gaze = ( ( int( inResponse[2] ), int( inResponse[4] ) ), ( int( inResponse[3] ), int( inResponse[5] ) ) )
		t = int( inResponse[0] )
		if startTime == None:
			startTime = t
			t = 0
		else:
			t = t - startTime
		x = []
		y = []
		ex = []
		ey = []
		ez = []

		dia = int( inResponse[6] ) > 0 and int( inResponse[7] ) > 0 and int( inResponse[8] ) > 0 and int( inResponse[9] ) > 0

		if screen_rect.collidepoint( int( inResponse[2] ), int( inResponse[4] ) ):
			x.append( int( inResponse[2] ) )
			y.append( int( inResponse[4] ) )
			ex.append( float( inResponse[10] ) )
			ey.append( float( inResponse[12] ) )
			ez.append( float( inResponse[14] ) )
		if screen_rect.collidepoint( int( inResponse[3] ), int( inResponse[5] ) ):
			x.append( int( inResponse[3] ) )
			y.append( int( inResponse[5] ) )
			ex.append( float( inResponse[11] ) )
			ey.append( float( inResponse[13] ) )
			ez.append( float( inResponse[15] ) )

		x = np.mean( x )
		y = np.mean( y )
		ex = np.mean( ex )
		ey = np.mean( ey )
		ez = np.mean( ez )

		fix, samp = fp.processData( t, dia, x, y, ex, ey, ez )

	def draw_text( text, font, color, loc, surf ):
		t = font.render( text, True, color )
		tr = t.get_rect()
		tr.center = loc
		surf.blit( t, tr )
		return tr

	def update():
		global state, angle1, angle2, gaze, fix, fp
		if state < 0:
			return
		for event in pygame.event.get():
			if event.type == pygame.KEYDOWN:
				if event.key == pygame.K_UP:
					fp.accThreshold += 0.5
				elif event.key == pygame.K_DOWN:
					fp.accThreshold -= 0.5
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
		#if gaze:
		#	pygame.draw.circle( screen, ( 255, 255, 0 ), gaze[0], 3, 1 )
		#	pygame.draw.circle( screen, ( 0, 255, 255 ), gaze[1], 3, 1 )
		if fix:
			pygame.draw.circle( screen, ( 255, 0, 0 ), map( int, fix ), 15, 2 )
		draw_text( "%d" % fp.accThreshold, f, ( 255, 255, 255 ), ( screen_rect.left + 50, screen_rect.bottom - 15 ), screen )
		draw_text( "%.2f" % fp.maxv, f, ( 255, 255, 255 ), ( screen_rect.left + 50, screen_rect.top + 15 ), screen )
		pygame.display.flip()

		angle1 += .05
		if angle1 >= 360:
			angle1 = 0

		angle2 -= .025
		if angle2 <= 0:
			angle2 = 360

	def cleanup( *args, **kwargs ):
		global fp
		fp.output.close()
		reactor.stop()

	def start( lc ):
		global state, update, client, cleanup
		state = 0
		client.addDispatcher( d )
		lc = LoopingCall( update )
		dd = lc.start( 1.0 / 30 )
		dd.addCallbacks( cleanup )

	client = iViewXClient( '192.168.1.100', 4444 )
	reactor.listenUDP( 5555, client )
	calibrator = Calibrator( client, screen, reactor = reactor, eye = 0 )
	fp = VelocityFP()
	calibrator.start( start )
	reactor.run()
