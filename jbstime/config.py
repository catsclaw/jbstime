from pathlib import Path
import os
import sys

import click
import yaml

from .error import Error


def load_config():
  config = {
    'username': None,
    'password': None,
  }

  # First try and load the config file
  config_file = Path.home() / '.jbstime' / 'config.yaml'

  try:
    yaml_config = yaml.safe_load(config_file.open())
    config.update(yaml_config)
  except FileNotFoundError:
    pass
  except:
    click.echo(f'Error reading {config_file} - please verify that it is a valid yaml file', err=True)
    sys.exit(Error.CONFIG_ERROR)

  # Then check the env variables
  config['username'] = os.environ.get('JBS_TIMETRACK_USER') or config['username']
  config['password'] = os.environ.get('JBS_TIMETRACK_PASS') or config['password']

  return config
