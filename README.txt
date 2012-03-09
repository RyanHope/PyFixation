==========
PyFixation
==========

``pyfixation`` is a Python package for classifying raw eye gaze data into discrete events like saccades and fixations.
This package can be used online in real-time or offline after data has been collected.

Here's a basic example of usage::

	from pyfixation import FixationProcessor

	px_per_mm = 3.55

	fp = FixationProcessor( px_per_mm, sample_rate = 500 )

	f = open( 'gazedata.txt', 'r' )
	for line in f.readlines():
		gaze_found, gaze_x, gaze_y = map( float, line.split( '\t' ) )
		print fp.detect_fixation( gaze_found, gaze_x, gaze_y )