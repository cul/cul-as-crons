from unittest.mock import MagicMock, patch
import requests

import pytest
from freezegun import freeze_time


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
    def test_all_repos(
        self,
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
        fa_ids = ["cul-1234", "BC-12-34"]
        response = repo_updater.update_index(fa_ids)
        mock_requests_post.assert_called_once_with(
            "https://findingaids.library.columbia.edu/api/v1/index/index_ead",
            json={"bibids": fa_ids},
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
        fa_ids = ["cul-1234", "BC-12-34"]
        repo_updater.update_index(fa_ids)
        mock_requests_post.assert_called_once_with(
            "https://findingaids.library.columbia.edu/api/v1/index/index_ead",
            json={"bibids": fa_ids},
            headers={
                "Authorization": "Token test",
                "Content-Type": "application/json",
            },
        )
        expected_error = (
            "Failed to index 1 collections: Detected nested collection components"
        )
        assert repo_updater.errors == [expected_error]

    @patch("crons.acfa_updater.requests.post")
    def test_update_index_http_error(self, mock_requests_post, repo_updater):
        mock_response = MagicMock(status_code=500, reason="Internal Server Error")
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "500 Error"
        )
        mock_requests_post.return_value = mock_response
        fa_ids = ["cul-1234"]

        repo_updater.update_index(fa_ids)

        expected_error = "Error indexing cul-1234: 500 Error"
        assert repo_updater.errors == [expected_error]

    def test_get_fa_id(self, repo_updater):
        test_cases = [
            ("1234", None, None, "cul-1234"),
            ("in2345", None, None, "cul-in2345"),
            ("BC12", None, None, "BC12"),
            ("BC", "23", None, "BC-23"),
            ("BC", "34", "56", "BC-34-56"),
        ]
        for id_0, id_1, id_2, expected_fa_id in test_cases:
            mock_resource = MagicMock(id_0=id_0)
            # Delete any attributes on mock_resource that are None
            if id_1 is not None:
                mock_resource.id_1 = id_1
            else:
                try:
                    del mock_resource.id_1
                except Exception:
                    pass
            if id_2 is not None:
                mock_resource.id_2 = id_2
            else:
                try:
                    del mock_resource.id_2
                except Exception:
                    pass
            actual_fa_id = repo_updater.get_fa_id(mock_resource)
            assert actual_fa_id == expected_fa_id, (
                f"Failed for input id_0='{id_0}', id_1='{id_1}', id_2='{id_2}'. "
                f"Expected '{expected_fa_id}', but got '{actual_fa_id}'."
            )

    @freeze_time("2026-01-02 12:00:00", tz_offset=0)
    @patch("crons.acfa_updater.UpdateRepository.update_index")
    @patch("crons.acfa_updater.yesterday_utc")
    def test_index_only_yesterday(
        self, mock_yesterday_utc, mock_update_index, repo_updater
    ):
        MOCKED_YESTERDAY_UTC = "2026-01-01T12:00:00Z"
        mock_yesterday_utc.return_value = MOCKED_YESTERDAY_UTC

        mock_as_client = repo_updater.as_client
        mock_resource_1 = MagicMock(id_0="1234", spec=["id_0"])
        mock_as_client.updated_resources.return_value = [mock_resource_1]

        repo_updater.index_only()

        mock_yesterday_utc.assert_called_once()
        mock_as_client.updated_resources.assert_called_once_with(MOCKED_YESTERDAY_UTC)
        mock_update_index.assert_called_once_with(["cul-1234"])

    @patch("crons.acfa_updater.Path")
    @patch("builtins.open", new_callable=MagicMock)
    def test_save_pdf_success(self, mock_open, MockPath, repo_updater):
        fa_id = "cul-1234"
        pdf_content = b"This is mocked PDF content"
        mock_pdf_response = MagicMock(content=pdf_content)
        repo_updater.as_client.create_pdf_job.return_value = mock_pdf_response
        mock_file_path = MockPath.return_value  # Path(self.pdf_cache, ...)
        mock_resource = MagicMock(id=1234)

        repo_updater.save_pdf(mock_resource, fa_id)

        repo_updater.as_client.create_pdf_job.assert_called_once_with(1234)
        expected_filename = f"as_ead_{fa_id}.pdf"
        MockPath.assert_called_once_with(repo_updater.pdf_cache, expected_filename)
        mock_open.assert_called_once_with(mock_file_path, "wb")
        mock_open.return_value.__enter__.return_value.write.assert_called_once_with(
            pdf_content
        )
        assert repo_updater.errors == []

    @patch("crons.acfa_updater.Path")
    @patch("builtins.open", new_callable=MagicMock)
    @patch("crons.acfa_updater.validate_against_schema")
    def test_save_ead_success(
        self, mock_validate_against_schema, mock_open, MockPath, repo_updater
    ):
        fa_id = "cul-1234"
        ead_content_bytes = b"<ead/>"
        ead_content_string = ead_content_bytes.decode("utf-8")
        mock_response = MagicMock()
        mock_response_content = MagicMock(spec=bytes)
        mock_response_content.__eq__ = MagicMock(return_value=True)
        mock_response_content.decode.return_value = ead_content_string
        mock_response.content = mock_response_content
        repo_updater.as_client.aspace.client.get.return_value = mock_response
        mock_validate_against_schema.return_value = True
        mock_file_path = MockPath.return_value
        mock_resource = MagicMock(id=1234)

        repo_updater.save_ead(mock_resource, fa_id)

        expected_url = f"/repositories/{repo_updater.repo.id}/resource_descriptions/{mock_resource.id}.xml"
        repo_updater.as_client.aspace.client.get.assert_called_once_with(
            expected_url, params=repo_updater.export_params
        )
        mock_validate_against_schema.assert_called_once_with(ead_content_bytes, "ead")
        expected_filename = f"as_ead_{fa_id}.xml"
        MockPath.assert_called_once_with(repo_updater.ead_cache, expected_filename)
        mock_open.assert_called_once_with(mock_file_path, "w")
        mock_open.return_value.__enter__.return_value.write.assert_called_once_with(
            ead_content_string
        )
        assert repo_updater.errors == []

    @patch("crons.acfa_updater.Path")
    @patch("builtins.open", new_callable=MagicMock)
    @patch("crons.acfa_updater.validate_against_schema")
    @patch("crons.acfa_updater.logging")
    def test_save_ead_invalid_ead(
        self,
        mock_logging,
        mock_validate_against_schema,
        mock_open,
        MockPath,
        repo_updater,
    ):
        fa_id = "cul-1234"
        ead_content_bytes = b"<ead/>"
        ead_content_string = ead_content_bytes.decode("utf-8")
        mock_response = MagicMock()
        mock_response_content = MagicMock(spec=bytes)
        mock_response_content.__eq__ = MagicMock(return_value=True)
        mock_response_content.decode.return_value = ead_content_string
        mock_response.content = mock_response_content
        repo_updater.as_client.aspace.client.get.return_value = mock_response
        mock_validate_against_schema.return_value = False  # Validation fails
        mock_resource = MagicMock(id=1234)

        repo_updater.save_ead(mock_resource, fa_id)

        mock_validate_against_schema.assert_called_once_with(ead_content_bytes, "ead")
        mock_logging.info.assert_called_once_with(f"{fa_id}: Invalid EAD")
        assert repo_updater.errors == [f"Invalid EAD: {fa_id}"]
        mock_open.assert_called_once()
        mock_open.return_value.__enter__.return_value.write.assert_called_once_with(
            ead_content_string
        )

    @freeze_time("2026-01-02 12:00:00", tz_offset=0)
    @patch("crons.acfa_updater.UpdateRepository.update_index")
    @patch("crons.acfa_updater.UpdateRepository.save_pdf")
    @patch("crons.acfa_updater.UpdateRepository.save_ead")
    @patch("crons.acfa_updater.yesterday_utc")
    def test_daily_update_success(
        self,
        mock_yesterday_utc,
        mock_save_ead,
        mock_save_pdf,
        mock_update_index,
        repo_updater,
    ):
        MOCKED_YESTERDAY_UTC = "2026-01-01T12:00:00Z"
        mock_yesterday_utc.return_value = MOCKED_YESTERDAY_UTC
        mock_resource_1 = MagicMock(id_0="1234", spec=["id_0"])
        mock_resource_2 = MagicMock(id_0="10815449", spec=["id_0"])
        mock_as_client = repo_updater.as_client
        mock_as_client.updated_resources.return_value = [
            mock_resource_1,
            mock_resource_2,
        ]

        repo_updater.get_fa_id = MagicMock(side_effect=["cul-1234", "cul-10815449"])

        errors = repo_updater.daily_update()
        mock_as_client.updated_resources.assert_called_once_with(MOCKED_YESTERDAY_UTC)
        assert mock_save_ead.call_count == 2
        mock_save_ead.assert_any_call(mock_resource_1, "cul-1234")
        mock_save_ead.assert_any_call(mock_resource_2, "cul-10815449")
        mock_save_pdf.assert_called_once_with(mock_resource_2, "cul-10815449")
        mock_update_index.assert_called_once_with(["cul-1234", "cul-10815449"])
        assert errors == []

    @patch("crons.acfa_updater.UpdateRepository.update_index")
    @patch("crons.acfa_updater.UpdateRepository.save_pdf")
    @patch("crons.acfa_updater.UpdateRepository.save_ead")
    @patch("crons.acfa_updater.yesterday_utc")
    @patch("crons.acfa_updater.logging")
    def test_daily_update_with_exception(
        self,
        mock_logging,
        mock_yesterday_utc,
        mock_save_ead,
        mock_save_pdf,
        mock_update_index,
        repo_updater,
    ):
        mock_yesterday_utc.return_value = "2026-01-01T12:00:00Z"
        mock_resource_1 = MagicMock(id_0="5678", spec=["id_0"])
        mock_resource_2 = MagicMock(id_0="9012", spec=["id_0"])
        repo_updater.as_client.updated_resources.return_value = [
            mock_resource_1,
            mock_resource_2,
        ]

        repo_updater.get_fa_id = MagicMock(side_effect=["cul-5678", "cul-9012"])

        mock_save_ead.side_effect = [
            None,
            Exception("Opening and ending tag mismatch"),
        ]
        errors = repo_updater.daily_update()
        assert mock_save_ead.call_count == 2
        mock_save_pdf.assert_not_called()
        mock_update_index.assert_called_once_with(["cul-5678"])
        expected_error_message = f"Error when processing cul-9012 ({repo_updater.repo.repo_code}): Opening and ending tag mismatch"
        assert errors == [expected_error_message]
        mock_logging.error.assert_called_once_with(
            "cul-9012: Opening and ending tag mismatch"
        )
