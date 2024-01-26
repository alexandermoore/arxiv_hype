import requests
from requests.adapters import HTTPAdapter, Retry
import pydantic
from datetime import datetime
from typing import List, Optional
import bs4
import time

from lib import arxiv
from lib import util
from lib.twitter import ArxivTweet


class TweetCredentials(pydantic.BaseModel):
    api_token: str = ...


def maybe_get(d, nested_keys, default=None):
    """For nested_keys=[k1, k2, ..., kn], returns
       d[k1][k2]...[kn] if it exists, and `default` otherwise.

    Args:
        d: Dict
        nested_keys: Keys to fetch
        default: Default to return if not found.
    """
    if d is None:
        return default
    for k in nested_keys:
        d = d.get(k)
        if d is None:
            return default
    return d


API_SEARCH_ENDPOINT = "https://api.twitter.com/2/tweets/search/recent"


class ApifyActor:
    def __init__(self):
        pass

    def extract_urls_from_tweet(self, tweet: dict):
        raise NotImplementedError()

    def get_arxiv_ids(self, tweet: dict):
        urls = self.extract_urls_from_tweet(tweet)
        results = []
        for url in urls:
            arxiv_ids = arxiv.maybe_text_to_arxiv_ids(url)
            if arxiv_ids:
                # will only find one ID in a single URL
                results.append(arxiv_ids[0])
        return results if len(results) else None


# TODO: Move functionality to ApifyActor so we can easily pick one to use at any given time.


class TwitterAPIV2:
    def __init__(self):
        self.credentials = TweetCredentials(
            api_token=util.get_env_var("APIFY_API_TOKEN")
        )

    @staticmethod
    def is_retweet(tweet):
        ref_tweets = tweet.get("referenced_tweets")
        if ref_tweets:
            for t in ref_tweets:
                if t["type"] == "retweeted":
                    return True
        return False

    @staticmethod
    def get_arxiv_ids(tweet, urls_field=["tweet_links"]):
        results = []
        urls = maybe_get(tweet, urls_field, [])
        for url in urls:
            arxiv_ids = arxiv.maybe_text_to_arxiv_ids(url)
            if arxiv_ids:
                # will only find one ID in a single URL
                results.append(arxiv_ids[0])
        return results if len(results) else None

    @staticmethod
    def maybe_parse_arxiv_tweet(tweet):
        arxiv_ids = TwitterAPIV2.get_arxiv_ids(tweet)
        if not arxiv_ids:
            return None
        tweet_id = tweet["tweet_id"]
        edited_ids = []  # [i for i in tweet["edit_history_tweet_ids"] if i != tweet_id]
        # metrics = tweet["public_metrics"]
        arxiv_tweet = ArxivTweet(
            tweet_id=tweet_id,
            arxiv_ids=arxiv_ids,
            edited_tweet_ids=edited_ids,
            created_at=util.iso_to_datetime(tweet["timestamp"]),
            likes=tweet["likes"],
            retweets=tweet["retweets"],
            quotes=tweet["quotes"],
            replies=tweet["replies"],
            impressions=0,
        )
        return arxiv_tweet

    def search_for_arxiv(self, start_time=None, end_time=None, max_results=10):
        responses = [
            self.api_search(
                query="arxiv.org",
                start_time=start_time,
                end_time=end_time,
                max_results=max_results,
            )
        ]

        arxiv_tweets = []
        seen = set()
        for response in responses:
            tweets = response
            print(f"Processing {len(tweets)} tweets...")

            # Get links from direct tweets. Right now we are just ignoring direct tweets
            # that point to reference tweets since their retweet/metric counts seem off.
            for tweet in tweets:
                parsed_tweet = self.maybe_parse_arxiv_tweet(tweet)
                if parsed_tweet is not None and parsed_tweet.tweet_id not in seen:
                    arxiv_tweets.append(parsed_tweet)
                    seen.add(parsed_tweet.tweet_id)
        return arxiv_tweets

    def api_search(
        self,
        query,
        max_results=5,
        has_engagement=None,
        min_likes=None,
        min_replies=None,
        min_retweets=None,
        start_time=None,
        end_time=None,
    ):
        # import json

        # with open("private/sample_apify_response2.json", "r") as f:
        #     return json.load(f)

        params = {
            "queries": [query],
            "max_tweets": max_results,
            "filter:has_engagement": has_engagement,
            "min_faves": min_likes,
            "min_replies": min_replies,
            "min_retweets": min_retweets,
            "language": "any",
            "use_experimental_scraper": False,
            "user_info": "user info and replying info",
            "max_attempts": 3,
            "newer_than": start_time,
            "older_than": end_time,
        }
        params = {k: v for k, v in params.items() if v is not None}
        timeout = 60 * 5
        launch_run_url = "https://api.apify.com/v2/acts/wHMoznVs94gOcxcZl/runs"

        def _dataset_url(run_id):
            return f"https://api.apify.com/v2/actor-runs/{run_id}/dataset/items"

        def _check_run_finished(run_id):
            url = f"https://api.apify.com/v2/actor-runs/{run_id}"
            result = self.request_raw(url, params={}, retries=1)
            return result["data"]["status"] == "SUCCEEDED"

        run_info = self.request_raw(
            launch_run_url, params=params, retries=1, request_type="post"
        )
        print("run_info:", run_info)
        run_id = run_info["data"]["id"]

        stime = time.time()
        while time.time() - stime <= timeout and not _check_run_finished(run_id):
            print(
                f"Waiting for run to complete... ({time.time() - stime}/{timeout} elapsed)"
            )
            time.sleep(10)
        results = self.request_raw(
            _dataset_url(run_id), params={"format": "json", "clean": "true"}
        )
        return results

    def request_raw(self, url, params, retries=3, request_type="get"):
        """Makes a request to the Twitter API with the appropriate credentials

        Args:
            url: API endpoint URL
            params: Dict of params for POST request
            retries: Number of retries

        Returns:
            Raw response as a dict.
        """
        with requests.Session() as s:
            retries = Retry(
                total=retries, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504]
            )
            s.mount("https://", HTTPAdapter(max_retries=retries))
            if request_type == "post":
                response = s.post(
                    url, params={"token": self.credentials.api_token}, json=params
                )
            elif request_type == "get":
                response = s.get(
                    url, params={**params, **{"token": self.credentials.api_token}}
                )
            else:
                raise ValueError(f"Invalid request type {request_type}")
        return response.json()


def getEmbeddedTweetHtml(tweet_id):
    with requests.Session() as s:
        retries = Retry(
            total=3, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504]
        )
        s.mount("https://", HTTPAdapter(max_retries=retries))
        try:
            response = s.get(
                "https://publish.twitter.com/oembed",
                params={"url": f"https://twitter.com/x/status/{tweet_id}"},
            )
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            raise err
    soup = bs4.BeautifulSoup(response.json()["html"])
    for link in soup.find_all("a"):
        link["target"] = "_blank"
    return str(soup)
