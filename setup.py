from setuptools import setup
from pyfixation import __version__ as version
import os.path

descr_file = os.path.join( os.path.dirname( __file__ ), 'README' )

setup( 
    name = 'PyFixation',
    version = version,

    packages = ['pyfixation'],

    description = 'A library for classifying raw eye gaze data into discrete events like saccades and fixations.',
    long_description = open( descr_file ).read(),
    author = 'Ryan Hope',
    author_email = 'rmh3093@gmail.com',
    url = 'https://github.com/RyanHope/PyFixation',
    classifiers = [
				'License :: OSI Approved :: GNU General Public License (GPL)',
				'Programming Language :: Python :: 2',
				'Topic :: Scientific/Engineering',
				'Topic :: Utilities',
    ],
	license = 'GPL-3',
	install_requires = [
					'scipy',
	],
 )
