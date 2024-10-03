"""Google Search Console data extractor module."""

from google.oauth2 import service_account
from googleapiclient.discovery import build
from lib.extractors.base import DataExtractor

class GSCExtractor(DataExtractor):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.service_account_file = config.api['service_account_file']
        self.subject_email = config.api['subject_email']
        self.credentials = None
        self.search_console_service = None
        self.top_n = config.top_n  # Read top_n parameter from config

    def authenticate(self):
        self.credentials = service_account.Credentials.from_service_account_file(
            self.service_account_file,
            scopes=['https://www.googleapis.com/auth/webmasters.readonly'],
            subject=self.subject_email
        )
        self.search_console_service = build('searchconsole', 'v1', credentials=self.credentials)
        self.is_authenticated = True

    def extract_data(self, page_url):
        self.check_authentication()

        # Query for overall metrics
        overall_request = {
            'startDate': self.config.start_date,
            'endDate': self.config.end_date,
            'dimensions': ['page'],
            'dimensionFilterGroups': [{
                'filters': [{
                    'dimension': 'page',
                    'operator': 'equals',
                    'expression': page_url
                }]
            }]
        }
        overall_response = self.search_console_service.searchanalytics().query(siteUrl=self.config.site_url, body=overall_request).execute()

        # Query for top queries
        query_request = {
            'startDate': self.config.start_date,
            'endDate': self.config.end_date,
            'dimensions': ['query'],
            'rowLimit': self.top_n,  # Limit top queries to top_n
            'dimensionFilterGroups': [{
                'filters': [{
                    'dimension': 'page',
                    'operator': 'equals',
                    'expression': page_url
                }]
            }]
        }
        query_response = self.search_console_service.searchanalytics().query(siteUrl=self.config.site_url, body=query_request).execute()

        overall_data = overall_response.get('rows', [{}])[0]

        return {
            "clicks": overall_data.get('clicks', 0),
            "impressions": overall_data.get('impressions', 0),
            "ctr": overall_data.get('ctr', 0),
            "avg_position": overall_data.get('position', 0),
            "ranking_keywords": [
                {
                    "query": row['keys'][0],
                    "clicks": row['clicks'],
                    "impressions": row['impressions'],
                    "ctr": row['ctr'],
                    "position": row['position']
                } for row in query_response.get('rows', [])[:self.top_n]  # Limit ranking_keywords to top_n
            ],
            "top_no_click_queries": [
                row['keys'][0] for row in sorted(
                    query_response.get('rows', []),
                    key=lambda x: x['impressions'] - x['clicks'],
                    reverse=True
                )[:self.top_n]  # Limit top_no_click_queries to top_n
            ]
        }