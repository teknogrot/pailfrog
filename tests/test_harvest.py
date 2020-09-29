"""Test harvesting functions of pailfrog."""
import os

from unittest.mock import (
    call,
    patch,
)

import pailfrog


@patch('pailfrog.requests.get')
@patch('pailfrog.dump_accessible_file')
def test_harvest_root(mock_dump_file, mock_req_get):
    """Test basic functionality of harvest root."""
    mock_req_get.side_effect = [
        FakeResponse(503, 'first_example'),
        FakeResponse(403, None),
        FakeResponse(200, 'index'),
        FakeResponse(404, None),
        FakeResponse(200, 'secret'),
    ]

    tests_root = os.path.dirname(__file__)
    base_bucket_path = os.path.join(tests_root, 'resources', 'base_bucket')
    with open(base_bucket_path) as bucket_handle:
        bucket_input = bucket_handle.read()

    results = pailfrog.harvest_root('http://something.test', bucket_input)

    expected_requests = [
        call('http://something.test/example1.html'),
        call('http://something.test/example2.html'),
        call('http://something.test/index.html'),
        call('http://something.test/robots.txt'),
        call('http://something.test/secret_page.html'),
    ]

    expected_dumps = [
        call('index', 'index.html'),
        call('secret', 'secret_page.html'),
    ]

    expected_results = {
        200: [
            'http://something.test/index.html',
            'http://something.test/secret_page.html',
        ],
        403: [
            'http://something.test/example2.html',
        ],
        404: [
            'http://something.test/robots.txt',
        ],
        503: [
            'http://something.test/example1.html',
        ],
    }

    assert expected_requests == mock_req_get.call_args_list
    assert expected_dumps == mock_dump_file.call_args_list
    assert expected_results == results


class FakeResponse:  # pylint: disable=too-few-public-methods
    """Fake requests response."""
    def __init__(self, status=200, content='test'):
        self.status_code = status
        self.content = content
