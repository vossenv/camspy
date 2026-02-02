import logging.config
import os
import shutil
import subprocess
import sys
from os.path import join

import click
from click_default_group import DefaultGroup
from dotenv import load_dotenv
from pathlib import Path
from camspy.config import load_config, ConfigValidationError
from camspy.process import StreamProcessor
from camspy.resources import get_resource
from camspy.utils import get_environment, init_logger


def log_meta(params, cfg):
    meta = get_environment()
    logging.info("App Version: {}".format(meta['app_version']))
    logging.info("Python Version: {}".format(meta['python_version']))
    logging.info("Platform: {0} / {1}".format(meta['os'], meta['os_version']))
    logging.info("CLI Parameters: " + str(params))
    logging.info("Options: {}".format(cfg))


def prompt_default_config(filename, output_path=None):
    if click.confirm("The specified configuration file '{}' does not exist.\n"
                     "Would you like to initialize the default configuration file with this name?".format(filename)):
        shutil.copy(get_resource('config_defaults.yaml'), join(output_path or os.getcwd(), 'config.yaml'))
        click.echo("Generated: {}".format(filename))


def init_config(params, config_filename):
    if not os.path.exists(config_filename):
        prompt_default_config(config_filename)
        exit()
    try:
        params['config_filename'] = config_filename = os.path.abspath(config_filename)
        cfg = load_config(config_filename)
        init_logger(cfg['logging'])
        log_meta(params, cfg)
        print(cfg['env_path'])
        load_dotenv(cfg['env_path'])
        return cfg
    except ConfigValidationError as e:
        logger = init_logger({})
        logger.critical(e)
        exit()


@click.group(cls=DefaultGroup, default='run', default_if_no_args=True, help="Spypy help text")
@click.pass_context
def cli(ctx):
    ctx.obj = {'help': ctx.get_help()}


@cli.command(help="Install as service")
@click.pass_context
@click.option('-d', '--dirname', default='.', type=str)
def install(ctx, dirname):
    p = Path(dirname).absolute()
    p.mkdir(parents=True, exist_ok=True)
    wd = p.as_posix()

    cfg_path = wd + os.sep + 'config.yaml'
    if not os.path.exists(cfg_path):
        shutil.copy(get_resource('config_defaults.yaml'), cfg_path)

    pypath = sys.executable

    venv_path = Path(pypath).parent / 'activate'
    startup = open(get_resource('camspy_startup.sh')).read()
    with open(wd + os.sep + 'camspy_startup.sh', 'w') as f:
        f.write(startup.format(venv_path.as_posix()))

    # shutil.copy(get_resource('camspy_startup.sh'), '.')
    svc = open(get_resource('camspy.service')).read()
    with open('camspy.service', 'w') as f:
        f.write(svc.format(launch_dir="{}".format(wd)))
    subprocess.check_output("sudo mv camspy.service /etc/systemd/system/camspy.service", shell=True)
    subprocess.check_output("sudo systemctl daemon-reload", shell=True)
    subprocess.check_output("sudo systemctl enable camspy.service", shell=True)
    subprocess.check_output("sudo chmod 777 -R {}".format(wd), shell=True)

    click.echo("Service installed!")
    try:
        subprocess.check_output("sudo service camspy status", shell=True)
    except subprocess.CalledProcessError as e:
        click.echo(e.output)

    click.echo("If service loaded successfully, start with 'sudo service camspy start'!")


@cli.command(help="Start the process")
@click.pass_context
@click.option('-c', '--config-filename', default='config.yaml', type=str)
def run(ctx, config_filename):
    cfg = init_config(ctx.params, config_filename)
    StreamProcessor(cfg).run()


if __name__ == "__main__":
    cli()
