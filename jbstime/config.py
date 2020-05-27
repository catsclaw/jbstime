import os
import pathlib
import sys

import click
import yaml

from .error import Error


def HOME():  # Needed for patching during tests
  return pathlib.Path.home() / '.jbstime'


def load_config():
  config = {
    'username': None,
    'password': None,
  }

  # First try and load the config file
  config_file = HOME() / 'config.yaml'

  try:
    yaml_config = yaml.safe_load(config_file.open())
    config.update(yaml_config)
  except FileNotFoundError:
    pass
  except Exception:
    click.echo(f'Error reading {config_file} - please verify that it is a valid yaml file', err=True)
    sys.exit(Error.CONFIG_ERROR)

  # Then check the env variables
  config['username'] = os.environ.get('JBS_TIMETRACK_USER') or config['username']
  config['password'] = os.environ.get('JBS_TIMETRACK_PASS') or config['password']

  return config


def save_holidays(holidays):
  if HOME().exists():
    holiday_file = HOME() / 'holidays.yaml'
    yaml.dump(holidays, holiday_file.open('w'))


def load_holidays():
  holiday_file = HOME() / 'holidays.yaml'
  if holiday_file.exists():
    return yaml.safe_load(holiday_file.open())

  return {}
