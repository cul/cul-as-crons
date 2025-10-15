from unittest.mock import MagicMock, patch

import pytest

from crons.acfa_updater import UpdateAllInstances, UpdateRepository


@pytest.fixture
def instance_updater():
    """Returns an initialized UpdateAllInstances object with ConfigParser mocked."""
    with patch("crons.acfa_updater.ConfigParser", autospec=True) as MockConfig:
        instance_updater = UpdateAllInstances("tmp/parent_cache")
        instance_updater.config = MockConfig.return_value
        return instance_updater


class TestUpdateAllInstances:

    def test_init(self):
        assert instance_updater

    @patch("crons.acfa_updater.UpdateAllInstances.send_error_email")
    @patch("crons.acfa_updater.UpdateRepository")
    @patch("crons.acfa_updater.ArchivesSpaceClient")
    @patch("crons.acfa_updater.ConfigParser")
    def test_all_repos(
        self,
        MockConfig,
        MockASClient,
        MockUpdateRepository,
        mock_send_email,
        instance_updater,
    ):
        instance_updater.config.sections.return_value = ["CUL"]
        instance_updater.config.__getitem__.return_value = {
            "baseurl": "https://example.com/api/",
            "username": "user",
            "password": "pass",
            "email_from": "test@example.com",
            "email_to": "test@example.com",
            "email_server": "smtp.example.com",
        }
        mock_repo = MagicMock()
        mock_as_client = MockASClient.return_value
        mock_as_client.aspace.repositories = [mock_repo]
        mock_updater_instance_1 = MockUpdateRepository.return_value
        mock_updater_instance_1.daily_update.return_value = ["Error message"]
        instance_updater.all_repos("test")
        MockASClient.assert_called_once_with("https://example.com/api/", "user", "pass")
        MockUpdateRepository.assert_called_once_with(
            "test", mock_as_client, mock_repo, "tmp/parent_cache"
        )
        mock_updater_instance_1.daily_update.assert_called_once()

    @patch("crons.acfa_updater.smtplib.SMTP")
    @patch("email.message.EmailMessage")
    def test_send_error_email(self, MockEmailMessage, MockSMTP, instance_updater):
        mock_message = MockEmailMessage.return_value
        mock_server = MockSMTP.return_value
        instance_updater.send_error_email(
            "from@example.com",
            "to@example.com",
            "smtp.example.com",
            ["Error 1", "Error 2"],
        )
        MockSMTP.assert_called_once_with(
            "smtp.example.com",
        )
        mock_server.quit.assert_called_once()
        expected_body = "The following errors occurred during the nightly finding aid update process:\n\nError 1\nError 2\n"
        mock_message.set_content.assert_called_once_with(expected_body)


@pytest.fixture
def repo_updater():
    """Returns an initialized UpdateRepository object and its required mocks."""
    mock_as_client = MagicMock()
    mock_repo = MagicMock(id=2, repo_code="TestRepo")
    repo_updater = UpdateRepository(
        "test", mock_as_client, mock_repo, "tmp/parent_cache"
    )
    return repo_updater


class TestUpdateRepository:

    def test_init(self, repo_updater):
        assert repo_updater
        assert repo_updater.acfa_api_token == "test"
        assert repo_updater.repo.id == 2
        assert str(repo_updater.ead_cache) == "tmp/parent_cache/ead_cache"
        assert repo_updater.errors == []

    @patch("crons.acfa_updater.requests.post")
    def test_update_index_success(self, mock_requests_post, repo_updater):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "success": 2,
            "failure": 0,
            "errorMessages": [],
        }
        mock_requests_post.return_value = mock_response
        bibids = ["cul-1234", "BC-12-34"]
        response = repo_updater.update_index(bibids)
        mock_requests_post.assert_called_once_with(
            "https://findingaids.library.columbia.edu/api/v1/index/index_ead",
            json={"bibids": bibids},
            headers={
                "Authorization": "Token test",
                "Content-Type": "application/json",
            },
        )
        assert repo_updater.errors == []
        assert response == mock_response

    @patch("crons.acfa_updater.requests.post")
    def test_update_index_failure(self, mock_requests_post, repo_updater):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "success": 1,
            "failure": 1,
            "errorMessages": ["Detected nested collection components"],
        }
        mock_requests_post.return_value = mock_response
        bibids = ["cul-1234", "BC-12-34"]
        repo_updater.update_index(bibids)
        mock_requests_post.assert_called_once_with(
            "https://findingaids.library.columbia.edu/api/v1/index/index_ead",
            json={"bibids": bibids},
            headers={
                "Authorization": "Token test",
                "Content-Type": "application/json",
            },
        )
        expected_error = (
            "Failed to index 1 collections: Detected nested collection components"
        )
        assert repo_updater.errors == [expected_error]
