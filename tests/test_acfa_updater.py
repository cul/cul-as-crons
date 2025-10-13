from unittest import TestCase
from unittest.mock import patch, MagicMock

from crons.acfa_updater import UpdateAllInstances, UpdateRepository


class TestUpdateAllInstances(TestCase):
    @patch("crons.acfa_updater.ConfigParser")
    def setUp(self, mock_config):
        self.instance_updater = UpdateAllInstances("tmp/parent_cache")

    def test_init(self):
        self.assertTrue(self.instance_updater)

    @patch("crons.acfa_updater.UpdateAllInstances.send_error_email")
    @patch("crons.acfa_updater.UpdateRepository")
    @patch("crons.acfa_updater.ArchivesSpaceClient")
    def test_all_repos(self, MockASClient, MockUpdateRepository, mock_send_email):
        self.instance_updater.config.sections.return_value = ["CUL"]
        self.instance_updater.config.__getitem__.return_value = {
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
        self.instance_updater.all_repos("test")
        MockASClient.assert_called_once_with("https://example.com/api/", "user", "pass")
        MockUpdateRepository.assert_called_once_with(
            "test", mock_as_client, mock_repo, "tmp/parent_cache"
        )
        mock_updater_instance_1.daily_update.assert_called_once()

    @patch("crons.acfa_updater.smtplib.SMTP")
    @patch("email.message.EmailMessage")
    def test_send_error_email(self, MockEmailMessage, MockSMTP):
        mock_message = MockEmailMessage.return_value
        mock_server = MockSMTP.return_value
        self.instance_updater.send_error_email(
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


class TestUpdateRepository(TestCase):
    def setUp(self):
        self.mock_as_client = MagicMock()
        self.mock_repo = MagicMock(id=2, repo_code="TestRepo")
        self.repo_updater = UpdateRepository(
            "test", self.mock_as_client, self.mock_repo, "tmp/parent_cache"
        )

    def test_init(self):
        self.assertTrue(self.repo_updater)
        self.assertEqual(self.repo_updater.acfa_api_token, "test")
        self.assertEqual(self.repo_updater.repo.id, 2)
        self.assertEqual(str(self.repo_updater.ead_cache), "tmp/parent_cache/ead_cache")
        self.assertEqual(self.repo_updater.errors, [])

    @patch("crons.acfa_updater.requests.post")
    def test_update_index_success(self, mock_requests_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "success": 2,
            "failure": 0,
            "errorMessages": [],
        }
        mock_requests_post.return_value = mock_response
        bibids = ["cul-1234", "BC-12-34"]
        response = self.repo_updater.update_index(bibids)
        mock_requests_post.assert_called_once_with(
            "https://findingaids.library.columbia.edu/api/v1/index/index_ead",
            json={"bibids": bibids},
            headers={
                "Authorization": "Token test",
                "Content-Type": "application/json",
            },
        )
        self.assertEqual(self.repo_updater.errors, [])
        self.assertEqual(response, mock_response)

    @patch("crons.acfa_updater.requests.post")
    def test_update_index_failure(self, mock_requests_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "success": 1,
            "failure": 1,
            "errorMessages": ["Detected nested collection components"],
        }
        mock_requests_post.return_value = mock_response
        bibids = ["cul-1234", "BC-12-34"]
        self.repo_updater.update_index(bibids)
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
        self.assertEqual(self.repo_updater.errors, [expected_error])
