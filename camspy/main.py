import logging.config
import os
import shutil
from os.path import join

import click
from click_default_group import DefaultGroup

from camspy.config import load_config, ConfigValidationError
from camspy.process import ImageProcessor, ImagePlayer, ImageWriter
from camspy.resources import get_resource
from camspy.utils import get_environment, init_logger

def log_meta(params, cfg):
    meta = get_environment()
    logging.info("App Version: {}".format(meta['app_version']))
    logging.info("Python Version: {}".format(meta['python_version']))
    logging.info("Platform: {0} / {1}".format(meta['os'], meta['os_version']))
    logging.info("CLI Parameters: " + str(params))
    logging.info("Options: {}".format(cfg))


def prompt_default_config(filename):
    if click.confirm("The specified configuration file '{}' does not exist.\n"
                     "Would you like to initialize the default configuration file with this name?".format(filename)):
        shutil.copy(get_resource('config_defaults.yaml'), join(os.getcwd(), 'config.yaml'))
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
        return cfg
    except ConfigValidationError as e:
        logger = init_logger({})
        logger.critical(e)
        exit()


@click.group(cls=DefaultGroup, default='run', default_if_no_args=True, help="Spypy help text")
@click.pass_context
def cli(ctx):
    ctx.obj = {'help': ctx.get_help()}


@cli.command(help="Start the process")
@click.pass_context
@click.option('-c', '--config-filename', default='config.yaml', type=str)
def run(ctx, config_filename):
    print("CAMSPY")
    cfg = init_config(ctx.params, config_filename)
    ImageProcessor(cfg).run()

@cli.command(help="Display the feed (requires display)")
@click.pass_context
@click.option('-c', '--config-filename', default='config.yaml', type=str)
def view(ctx, config_filename):
    cfg = init_config(ctx.params, config_filename)
    ImagePlayer(cfg).run()

@cli.command(help="Write some test images")
@click.pass_context
@click.option('-c', '--config-filename', default='config.yaml', type=str)
@click.option('-n', '--number', default=1, type=int)
def writeimage(ctx, config_filename, number):
    cfg = init_config(ctx.params, config_filename)
    ImageWriter(cfg).write_images(number)

if __name__ == "__main__":
    cli()
