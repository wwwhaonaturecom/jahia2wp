"""All rights reserved. ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE, Switzerland, VPSI, 2017
jahia2wp: an amazing tool !

Usage:
  jahia2wp.py download              <site>                          [--debug | --quiet]
    [--username=<USERNAME> --host=<HOST> --zip-path=<ZIP_PATH> --force]
  jahia2wp.py unzip                 <site>                          [--debug | --quiet]
    [--username=<USERNAME> --host=<HOST> --zip-path=<ZIP_PATH> --force]
    [--output-dir=<OUTPUT_DIR>]
  jahia2wp.py parse                 <site>                          [--debug | --quiet]
    [--output-dir=<OUTPUT_DIR>] [--print-report]
    [--use-cache] [--site-path=<SITE_PATH>]
  jahia2wp.py export                <site>                          [--debug | --quiet]
    [--to-wordpress | --clean-wordpress]
    [--admin-password=<PASSWORD>]
    [--site-host=<SITE_HOST> --site-path=<SITE_PATH>]
    [--output-dir=<OUTPUT_DIR>]
    [--installs-locked=<BOOLEAN> --updates-automatic=<BOOLEAN>]
    [--openshift-env=<OPENSHIFT_ENV>]
    [--theme=<THEME> --unit-name=<UNIT_NAME> --wp-site-url=<WP_SITE_URL>]
  jahia2wp.py clean                 <wp_env> <wp_url>               [--debug | --quiet]
    [--stop-on-errors]
  jahia2wp.py check                 <wp_env> <wp_url>               [--debug | --quiet]
  jahia2wp.py generate              <wp_env> <wp_url>               [--debug | --quiet]
    [--wp-title=<WP_TITLE> --wp-tagline=<WP_TAGLINE> --admin-password=<PASSWORD>]
    [--theme=<THEME> --theme-faculty=<THEME-FACULTY>]
    [--installs-locked=<BOOLEAN> --automatic-updates=<BOOLEAN>]
    [--extra-config=<YAML_FILE>]
  jahia2wp.py backup                <wp_env> <wp_url>               [--debug | --quiet]
  jahia2wp.py version               <wp_env> <wp_url>               [--debug | --quiet]
  jahia2wp.py admins                <wp_env> <wp_url>               [--debug | --quiet]
  jahia2wp.py generate-many         <csv_file>                      [--debug | --quiet]
  jahia2wp.py export-many           <csv_file>                      [--debug | --quiet]
    [--output-dir=<OUTPUT_DIR>]
  jahia2wp.py backup-many           <csv_file>                      [--debug | --quiet]
  jahia2wp.py rotate-backup         <csv_file>          [--dry-run] [--debug | --quiet]
  jahia2wp.py veritas               <csv_file>                      [--debug | --quiet]
  jahia2wp.py inventory             <path>                          [--debug | --quiet]
  jahia2wp.py extract-plugin-config <wp_env> <wp_url> <output_file> [--debug | --quiet]
  jahia2wp.py list-plugins          <wp_env> <wp_url>               [--debug | --quiet]
    [--config [--plugin=<PLUGIN_NAME>]] [--extra-config=<YAML_FILE>]
  jahia2wp.py update-plugins        <wp_env> <wp_url>               [--debug | --quiet]
    [--force] [--plugin=<PLUGIN_NAME>]
  jahia2wp.py update-plugins-many   <csv_file>                      [--debug | --quiet]
    [--force] [--plugin=<PLUGIN_NAME>]

Options:
  -h --help                 Show this screen.
  -v --version              Show version.
  --debug                   Set log level to DEBUG [default: INFO]
  --quiet                   Set log level to WARNING [default: INFO]
"""
import getpass
import logging
import pickle

import os
import yaml
from docopt import docopt
from docopt_dispatch import dispatch
from epflldap.ldap_search import get_unit_id
from rotate_backups import RotateBackups

import settings
from crawler import JahiaCrawler
from exporter.wp_exporter import WPExporter
from parser.jahia_site import Site
from settings import VERSION, FULL_BACKUP_RETENTION_THEME, INCREMENTAL_BACKUP_RETENTION_THEME, \
    DEFAULT_THEME_NAME, DEFAULT_CONFIG_INSTALLS_LOCKED, DEFAULT_CONFIG_UPDATES_AUTOMATIC
from unzipper.unzip import unzip_one
from utils import Utils
from veritas.casters import cast_boolean
from veritas.veritas import VeritasValidor
from wordpress import WPSite, WPConfig, WPGenerator, WPBackup, WPPluginConfigExtractor


def _check_site(wp_env, wp_url, **kwargs):
    """ Helper function to validate wp site given arguments """
    wp_site = WPSite(wp_env, wp_url, wp_site_title=kwargs.get('wp_title'))
    wp_config = WPConfig(wp_site)
    if not wp_config.is_installed:
        raise SystemExit("No files found for {}".format(wp_site.url))
    if not wp_config.is_config_valid:
        raise SystemExit("Configuration not valid for {}".format(wp_site.url))
    return wp_config


def _check_csv(csv_file, **kwargs):
    """
    Check validity of CSV file containing sites information

    Arguments keywords
    csv_file -- Path to CSV file

    Return
    Instance of VeritasValidator
    """
    validator = VeritasValidor(csv_file)

    # If errors found during validation
    if not validator.validate():
        for error in validator.errors:
            logging.error(error.message)
        raise SystemExit("Invalid CSV file!")

    return validator


def _add_extra_config(extra_config_file, current_config, **kwargs):
    """ Adds extra configuration information to current config

    Arguments keywords:
    extra_config_file -- YAML file in which is extra config
    current_config -- dict with current configuration

    Return:
    current_config dict merge with YAML file content"""
    if not os.path.exists(extra_config_file):
        raise SystemExit("Extra config file not found: {}".format(extra_config_file))

    extra_config = yaml.load(open(extra_config_file, 'r'))

    return {**current_config, **extra_config}


@dispatch.on('download')
def download(site, username=None, host=None, zip_path=None, force=False, **kwargs):
    # prompt for password if username is provided
    password = None
    if username is not None:
        password = getpass.getpass(prompt="Jahia password for user '{}': ".format(username))
    crawler = JahiaCrawler(site, username=username, password=password, host=host, zip_path=zip_path, force=force)
    return crawler.download_site()


@dispatch.on('unzip')
def unzip(site, username=None, host=None, zip_path=None, force=False, output_dir=None, **kwargs):

    # get zip file
    zip_file = download(site, username, host, zip_path, force)

    if output_dir is None:
        output_dir = settings.JAHIA_DATA_PATH

    try:
        unzipped_files = unzip_one(output_dir, site, zip_file)
    except Exception as err:
        logging.error("%s - unzip - Could not unzip file - Exception: %s", site, err)

    # return results
    return unzipped_files


@dispatch.on('parse')
def parse(site, output_dir=None, print_report=None, use_cache=None, host=None, site_path=None, **kwargs):
    """
    Parse the give site.
    """
    try:
        # create subdir in output_dir
        site_dir = unzip(site=site, output_dir=output_dir, host=host)

        # where to cache our parsing
        pickle_file = os.path.join(site_dir, 'parsed_%s.pkl' % site)

        # when using-cache: check if already parsed
        if use_cache:
            if os.path.exists(pickle_file):
                with open(pickle_file, 'rb'):
                    logging.info("Loaded parsed site from %s" % pickle_file)

        logging.info("Parsing Jahia xml files from %s...", site_dir)
        site = Site(site_dir, site)

        print(site.report)

        # always save the parsed data on disk, so we can use the
        # cache later if we want
        with open(pickle_file, 'wb') as output:
            logging.info("Parsed site saved into %s" % pickle_file)
            pickle.dump(site, output, pickle.HIGHEST_PROTOCOL)

        # log success
        logging.info("Site %s successfully parsed" % site)

        return site

    except Exception as err:
        logging.error("%s - parse - Exception: %s", site, err)
        raise err


@dispatch.on('export')
def export(
        site,
        to_wordpress=False, clean_wordpress=False,
        admin_password=None,
        site_host=None, site_path=None,
        output_dir=None,
        theme=None, unit_name=None, wp_site_url=None, installs_locked=False, updates_automatic=False, openshift_env=None,
        **kwargs):

    """
    :param site: 
    :param to_wordpress: 
    :param clean_wordpress: 
    :param admin_password: 
    :param site_host: 
    :param site_path: 
    :param output_dir: 
    :param theme: 
    :param unit_name: 
    :param wp_site_url: 
    :param installs_locked: 
    :param updates_automatic: 
    :param openshift_env: 
    :param kwargs: 
    :return: 
    """

    def get_lang_by_default(languages):
        """
        Return the default language
        
        If the site is in multiple languages, English is the default language
        """
        if len(languages) == 1:
            return languages[0]
        elif "en" in languages:
            return "en"
        else:
            return languages[0]

    def get_host(site_host):
        """
        Return the host of the WordPress site
        """
        if site_host is None or 'localhost' in site_host:
            return settings.HTTPD_CONTAINER
        return site_host

    def install_basic_auth_plugin():
        """
        Install basic auth plugin

        This plugin is used to communicate with REST API of WordPress site.
        """
        zip_path = os.path.join(settings.EXPORTER_DATA_PATH, 'Basic-Auth.zip')
        cmd = "plugin install --activate {}".format(zip_path)
        wp_generator.run_wp_cli(cmd)
        logging.debug("Basic-Auth plugin is installed and activated")

    def active_dual_auth_for_dev_only():
        """
        Active dual authenticate for development only
        """
        if settings.LOCAL_ENVIRONMENT:
            cmd = "option update plugin:epfl_tequila:has_dual_auth 1"
            wp_generator.run_wp_cli(cmd)
            logging.debug("Dual authenticate is activated")

    def uninstall_basic_auth_plugin():
        """
        Uninstall basic auth plugin

        This plugin is used to communicate with REST API of WordPress site.
        """
        # Deactivate basic-auth plugin
        cmd = "plugin deactivate Basic-Auth"
        wp_generator.run_wp_cli(cmd)
        logging.debug("Basic-Auth plugin is deactivated")

        # Uninstall basic-auth plugin
        cmd = "plugin uninstall Basic-Auth"
        wp_generator.run_wp_cli(cmd)
        logging.debug("Basic-Auth plugin is uninstalled")

    # Download, Unzip the jahia zip and parse the xml data
    site = parse(site=site, host=site_host)

    if settings.LOCAL_ENVIRONMENT:
        site_host = get_host(site_host=None)
        openshift_env = settings.OPENSHIFT_ENV
        wp_site_url = "http://{}/{}".format(site_host, site.name)
        installs_locked = False
        updates_automatic = False
        admin_password = "admin"
        unit_name = site.name

    info = {
        # info from parser
        'langs': ",".join(site.languages),
        'wp_site_title': site.acronym[get_lang_by_default(site.languages)],
        'wp_tagline': site.title[get_lang_by_default(site.languages)],
        'theme_faculty': site.theme[get_lang_by_default(site.languages)],
        'unit_name': unit_name,

        # info from source of truth
        'openshift_env': openshift_env,
        'wp_site_url': wp_site_url,
        'theme': theme,
        'updates_automatic': updates_automatic,
        'installs_locked': installs_locked,

        # info determined
        'unit_id': get_unit_id(unit_name),
    }

    # Generate a WordPress site
    wp_generator = WPGenerator(info, admin_password)
    wp_generator.generate()

    install_basic_auth_plugin()
    active_dual_auth_for_dev_only()

    if to_wordpress:
        logging.info("Exporting %s to WordPress...", site.name)
        wp_exporter = WPExporter(
            site,
            site_host,
            site_path,
            output_dir,
            wp_generator
        )
        wp_exporter.import_all_data_to_wordpress()
        logging.info("Site %s successfully exported to WordPress", site.name)

    if clean_wordpress:
        logging.info("Cleaning WordPress for %s...", site.name)
        wp_exporter = WPExporter(
            site,
            site_host,
            site_path,
            output_dir,
            wp_generator
        )
        wp_exporter.delete_all_content()
        logging.info("Data of WordPress site %s successfully deleted", site.name)

    uninstall_basic_auth_plugin()


@dispatch.on('export-many')
def export_many(csv_file, output_dir=None, **kwargs):

    # FIXME: output_dir is None, read a environment variable

    # FIXME : validation
    # CSV file validation
    # validator = _check_csv(csv_file)
    rows = Utils.csv_filepath_to_dict(csv_file)

    # create a new WP site for each row

    # FIXME: dès que veritas a été adapté
    # print("\n{} websites will now be generated...".format(len(validator.rows)))
    # for index, row in enumerate(validator.rows):
    for index, row in enumerate(rows):

        print("\nIndex #{}:\n---".format(index))
        # CSV file is utf-8 so we encode correctly the string to avoid errors during logging.debug display
        row_bytes = repr(row).encode('utf-8')
        logging.debug("%s - row %s: %s", row["wp_site_url"], index, row_bytes)

        export(
            site=row['Jahia_zip'],
            to_wordpress=True,
            clean_wordpress=False,
            site_host=None,
            site_path=None,
            output_dir=output_dir,
            unit_name=row['unit_name'],
            theme=row['theme'],
            installs_locked=row['installs_locked'],
            updates_automatic=row['updates_automatic'],
            wp_site_url=row['wp_site_url'],
            openshift_env= row['openshift_env'],
        )


@dispatch.on('check')
def check(wp_env, wp_url, **kwargs):
    wp_config = _check_site(wp_env, wp_url, **kwargs)
    # run a few more tests
    if not wp_config.is_install_valid:
        raise SystemExit("Could not login or use site at {}".format(wp_config.wp_site.url))
    # success case
    print("WordPress site valid and accessible at {}".format(wp_config.wp_site.url))


@dispatch.on('clean')
def clean(wp_env, wp_url, stop_on_errors=False, **kwargs):
    # when forced, do not check the status of the config -> just remove everything possible
    if stop_on_errors:
        _check_site(wp_env, wp_url, **kwargs)
    # config found: proceed with cleaning
    # FIXME: Il faut faire un clean qui n'a pas besoin de unit_name
    wp_generator = WPGenerator({'openshift_env': wp_env, 'wp_site_url': wp_url})
    if wp_generator.clean():
        print("Successfully cleaned WordPress site {}".format(wp_generator.wp_site.url))


@dispatch.on('generate')
def generate(wp_env, wp_url,
             wp_title=None, wp_tagline=None, admin_password=None,
             theme=None, theme_faculty=None,
             installs_locked=None, updates_automatic=None,
             extra_config=None,
             **kwargs):
    """
    This command may need more params if reference to them are done in YAML file. In this case, you'll see an
    error explaining which params are needed and how they can be added to command line
    """

    # if nothing is specified we want a locked install
    if installs_locked is None:
        installs_locked = DEFAULT_CONFIG_INSTALLS_LOCKED
    else:
        installs_locked = cast_boolean(installs_locked)

    # if nothing is specified we want automatic updates
    if updates_automatic is None:
        updates_automatic = DEFAULT_CONFIG_UPDATES_AUTOMATIC
    else:
        updates_automatic = cast_boolean(updates_automatic)

    # FIXME: When we will use 'unit_id' from CSV file, add parameter here OR dynamically get it from AD
    all_params = {'openshift_env': wp_env,
                  'wp_site_url': wp_url,
                  'theme': theme or DEFAULT_THEME_NAME,
                  'installs_locked': installs_locked,
                  'updates_automatic': updates_automatic}

    # Adding parameters if given
    if theme_faculty is not None:
        all_params['theme_faculty'] = theme_faculty

    if wp_title is not None:
        all_params['wp_site_title'] = wp_title

    if wp_tagline is not None:
        all_params['wp_tagline'] = wp_tagline

    # if we have extra configuration to load,
    if extra_config is not None:
        all_params = _add_extra_config(extra_config, all_params)

    wp_generator = WPGenerator(all_params, admin_password=admin_password)

    if not wp_generator.generate():
        raise SystemExit("Generation failed. More info above")

    print("Successfully created new WordPress site at {}".format(wp_generator.wp_site.url))


@dispatch.on('backup')
def backup(wp_env, wp_url, **kwargs):
    wp_backup = WPBackup(wp_env, wp_url)
    if not wp_backup.backup():
        raise SystemExit("Backup failed. More info above")

    print("Successfull {} backup for {}".format(
        wp_backup.backup_pattern, wp_backup.wp_site.url))


@dispatch.on('version')
def version(wp_env, wp_url, **kwargs):
    wp_config = _check_site(wp_env, wp_url, **kwargs)
    # success case
    print(wp_config.wp_version)


@dispatch.on('admins')
def admins(wp_env, wp_url, **kwargs):
    wp_config = _check_site(wp_env, wp_url, **kwargs)
    # success case
    for admin in wp_config.admins:
        print(admin)


@dispatch.on('generate-many')
def generate_many(csv_file, **kwargs):

    # CSV file validation
    validator = _check_csv(csv_file)

    # create a new WP site for each row
    print("\n{} websites will now be generated...".format(len(validator.rows)))
    for index, row in enumerate(validator.rows):
        print("\nIndex #{}:\n---".format(index))
        # CSV file is utf-8 so we encode correctly the string to avoid errors during logging.debug display
        row_bytes = repr(row).encode('utf-8')
        logging.debug("%s - row %s: %s", row["wp_site_url"], index, row_bytes)
        WPGenerator(row).generate()


@dispatch.on('backup-many')
def backup_many(csv_file, **kwargs):

    # CSV file validation
    validator = _check_csv(csv_file)

    # create a new WP site backup for each row
    print("\n{} websites will now be backuped...".format(len(validator.rows)))
    for index, row in enumerate(validator.rows):
        logging.debug("%s - row %s: %s", row["wp_site_url"], index, row)
        WPBackup(
            row["openshift_env"],
            row["wp_site_url"]
        ).backup()


@dispatch.on('rotate-backup')
def rotate_backup(csv_file, dry_run=False, **kwargs):

    # CSV file validation
    validator = _check_csv(csv_file)

    for index, row in enumerate(validator.rows):
        path = WPBackup(row["openshift_env"], row["wp_site_url"]).path
        # rotate full backups first
        for pattern in ["*full.sql", "*full.tar"]:
            RotateBackups(
                FULL_BACKUP_RETENTION_THEME,
                dry_run=dry_run,
                include_list=[pattern]
            ).rotate_backups(path)
        # rotate incremental backups
        for pattern in ["*.list", "*inc.sql", "*inc.tar"]:
            RotateBackups(
                INCREMENTAL_BACKUP_RETENTION_THEME,
                dry_run=dry_run,
                include_list=[pattern]
            ).rotate_backups(path)


@dispatch.on('inventory')
def inventory(path, **kwargs):
    logging.info("Building inventory...")
    print(";".join(['path', 'valid', 'url', 'version', 'db_name', 'db_user', 'admins']))
    for site_details in WPConfig.inventory(path):
        print(";".join([
            site_details.path,
            site_details.valid,
            site_details.url,
            site_details.version,
            site_details.db_name,
            site_details.db_user,
            site_details.admins
        ]))
    logging.info("Inventory made for %s", path)


@dispatch.on('veritas')
def veritas(csv_file, **kwargs):
    validator = VeritasValidor(csv_file)

    if not validator.validate():
        validator.print_errors()
    else:
        print("CSV file validated!")


@dispatch.on('extract-plugin-config')
def extract_plugin_config(wp_env, wp_url, output_file, **kwargs):

    ext = WPPluginConfigExtractor(wp_env, wp_url)

    ext.extract_config(output_file)


@dispatch.on('list-plugins')
def list_plugins(wp_env, wp_url, config=False, plugin=None, extra_config=None, **kwargs):
    """
    This command may need more params if reference to them are done in YAML file. In this case, you'll see an
    error explaining which params are needed and how they can be added to command line
    """

    # FIXME: When we will use 'unit_id' from CSV file, add parameter here OR dynamically get it from AD
    all_params = {'openshift_env': wp_env,
                  'wp_site_url': wp_url}

    # if we have extra configuration to load,
    if extra_config is not None:
        all_params = _add_extra_config(extra_config, all_params)

    print(WPGenerator(all_params).list_plugins(config, plugin))


@dispatch.on('update-plugins')
def update_plugins(wp_env, wp_url, plugin=None, force=False, **kwargs):

    _check_site(wp_env, wp_url, **kwargs)

    wp_generator = WPGenerator({'openshift_env': wp_env,
                                'wp_site_url': wp_url})

    wp_generator.update_plugins(only_one=plugin, force=force)

    print("Successfully updated WordPress plugin list at {}".format(wp_generator.wp_site.url))


@dispatch.on('update-plugins-many')
def update_plugins_many(csv_file, plugin=None, force=False, **kwargs):

    # CSV file validation
    validator = _check_csv(csv_file)

    # Update WP site plugins for each row
    print("\n{} websites will now be updated...".format(len(validator.rows)))
    for index, row in enumerate(validator.rows):
        print("\nIndex #{}:\n---".format(index))
        logging.debug("%s - row %s: %s", row["wp_site_url"], index, row)
        WPGenerator(row).update_plugins(only_one=plugin, force=force)


if __name__ == '__main__':

    # docopt return a dictionary with all arguments
    # __doc__ contains package docstring
    args = docopt(__doc__, version=VERSION)

    # set logging config before anything else
    Utils.set_logging_config(args)

    logging.debug(args)

    dispatch(__doc__)
