import numpy as np
import scipy, scipy.signal

def calc_coeff( window_size, order, deriv = 0 ):
	"""
	calculates filter coefficients for symmetric savitzky-golay filter.
	see: http://www.nrbook.com/a/bookcpdf/c14-8.pdf

	window_size   means that 2*num_points+1 values contribute to the
				  smoother.

	order	      is degree of fitting polynomial

	deriv   	  is degree of implicit differentiation.
				  0 means that filter results in smoothing of function
				  1 means that filter results in smoothing the first
											 derivative of function.
				  and so on ...
	"""
	try:
		window_size = np.abs( np.int( window_size ) )
		order = np.abs( np.int( order ) )
	except ValueError, msg:
		raise ValueError( "window_size and order have to be of type int" )
	if window_size % 2 != 1 or window_size < 1:
		raise TypeError( "window_size size must be a positive odd number" )
	if window_size < order + 2:
		raise TypeError( "window_size is too small for the polynomials order" )
	order_range = range( order + 1 )
	half_window = ( window_size - 1 ) // 2
	b = np.mat( [[k ** i for i in order_range] for k in range( -half_window, half_window + 1 )] )
	return half_window, np.linalg.pinv( b ).A[deriv]


def filter( signal, (half_window, coeff) ):

	"""applies coefficients calculated by calc_coeff() to signal"""

    # pad the signal at the extremes with
    # values taken from the signal itself
	firstvals = signal[0] - np.abs( signal[1:half_window + 1][::-1] - signal[0] )
	lastvals = signal[-1] + np.abs( signal[-half_window - 1:-1][::-1] - signal[-1] )
	signal = np.concatenate( ( firstvals, signal, lastvals ) )
	return np.convolve( coeff, signal, mode = 'valid' )