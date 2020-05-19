import setuptools

setuptools.setup(
  name='jbstime',
  version='0.1',
  py_modules=['jbstime'],
  description='A command-line interface to JBS timesheets.',
  packages=setuptools.find_packages(),
  install_requires=[
    'bs4',
    'click',
    'python-dateutil',
    'requests',
    'pyyaml',
  ],
  extras_require={
      'test': [
        'flake8',
        'pytest',
        'pytest-cov',
        'requests-mock',
      ],
  },
  entry_points='''
    [console_scripts]
    jbstime=jbstime.client:_exec
  ''',
)
