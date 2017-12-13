# coding=utf-8
"""Tests that re-publish repositories."""
import random
import unittest
from urllib.parse import urljoin

from pulp_smash import api, config, utils
from pulp_smash.constants import RPM_UNSIGNED_FEED_URL
from pulp_smash.tests.pulp2.constants import REPOSITORY_PATH
from pulp_smash.tests.pulp2.rpm.api_v2.utils import (
    gen_distributor,
    gen_repo,
    get_unit,
)
from pulp_smash.tests.pulp2.rpm.utils import (
    check_issue_2277,
    check_issue_2620,
    check_issue_3104,
)
from pulp_smash.tests.pulp2.rpm.utils import set_up_module as setUpModule  # noqa pylint:disable=unused-import


class UnassociateTestCase(unittest.TestCase):
    """Republish a repository after removing content.

    Specifically, this test case does the following:

    1. Create, populate and publish a repository.
    2. Pick a content unit from the repository and verify it can be downloaded.
    3. Remove the content unit from the repository, and re-publish it, and
       verify that it can't be downloaded.
    """

    def test_all(self):
        """Republish a repository after removing content."""
        cfg = config.get_config()
        if check_issue_3104(cfg):
            raise unittest.SkipTest('https://pulp.plan.io/issues/3104')
        if check_issue_2277(cfg):
            raise unittest.SkipTest('https://pulp.plan.io/issues/2277')
        if check_issue_2620(cfg):
            raise unittest.SkipTest('https://pulp.plan.io/issues/2620')

        # Create, sync and publish a repository.
        client = api.Client(cfg, api.json_handler)
        body = gen_repo()
        body['importer_config']['feed'] = RPM_UNSIGNED_FEED_URL
        body['distributors'] = [gen_distributor()]
        repo = client.post(REPOSITORY_PATH, body)
        self.addCleanup(client.delete, repo['_href'])
        repo = client.get(repo['_href'], params={'details': True})
        utils.sync_repo(cfg, repo)
        utils.publish_repo(cfg, repo)

        # Pick a random content unit and verify it's accessible.
        unit = random.choice(
            utils.search_units(cfg, repo, {'type_ids': ('rpm',)})
        )
        filename = unit['metadata']['filename']
        get_unit(cfg, repo['distributors'][0], filename)

        # Remove the content unit and verify it's inaccessible.
        client.post(
            urljoin(repo['_href'], 'actions/unassociate/'),
            {'criteria': {'filters': {'unit': {'filename': filename}}}},
        )
        utils.publish_repo(cfg, repo)
        with self.assertRaises(KeyError):
            get_unit(cfg, repo['distributors'][0], filename)
