from setuptools import setup

setup(
    name='jbstime',
    version='0.1',
    py_modules=['jbstime'],
    install_requires=[
      'bs4',
      'click',
      'python-dateutil',
      'requests',
    ],
    entry_points='''
        [console_scripts]
        jbstime=jbstime.jbstime:cli
    ''',
)
