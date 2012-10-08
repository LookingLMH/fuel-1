import logging
from time import sleep
import unittest
from devops.helpers import ssh, os
import re
from ci_helpers import get_environment
from helpers import load, execute, write_config, sync_time
from root import root

class RecipeTestCase(unittest.TestCase):

    def setUp(self):
        self.environment = get_environment()
        master = self.environment.node['master']
        self.revert_snapshot()
        self.master_remote = ssh(master.ip_address, username='root', password='r00tme')
        self.upload_recipes()
        self.restart_puppet_muster()

    def upload_recipes(self):
        recipes_dir = root('fuel','deployment','puppet')
        for dir in os.listdir(recipes_dir):
            recipe_dir = os.path.join(recipes_dir, dir)
            remote_dir = "/etc/puppet/modules/"
            self.master_remote.mkdir(remote_dir)
            self.master_remote.upload(recipe_dir, remote_dir)

    def revert_snapshot(self):
        for node in self.environment.nodes:
            node.restore_snapshot('empty')
            sleep(4)
            sync_time(ssh(node.ip_address, username='root', password='r00tme').sudo.ssh)

    def replace(self, template, **kwargs):
        for key in kwargs:
            value=kwargs.get(key)
            template, count = re.subn(
                '^(\$' + str(key) + ')\s*=.*', "\\1 = " + str(value),
                template,
                flags=re.MULTILINE)
            if count == 0:
                raise Exception("Variable ${0:>s} is not found".format(key))
        return template

    def write_site_pp_manifest(self, path, **kwargs):
        site_pp = load(path)
        site_pp = self.replace(site_pp, **kwargs)
        write_config(self.master_remote, '/etc/puppet/manifests/site.pp', site_pp)

    def assertResult(self, result):
        self.assertEqual([], result['stderr'], result['stderr'])
        errors, warnings = self.parse_out(result['stdout'])
        self.assertEqual([], errors, errors)
        self.assertEqual([], warnings, warnings)

    def parse_out(self, out):
        errors = []
        warnings = []
        for line in out:
            logging.info(line)
            if line.find('err: ') !=-1:
                errors.append(line)
            if line.find('warning: ') !=-1:
                warnings.append(line)
        return errors, warnings

    def restart_puppet_muster(self):
        execute(self.master_remote, 'service puppetmaster restart')
