import requests
from requests.adapters import HTTPAdapter, Retry
import pydantic
import yaml
import json
import math
from datetime import datetime
from typing import List, Optional

from lib import arxiv
from lib import util

class TweetCredentials(pydantic.BaseModel):
    bearer_token: str = ...
    consumer_key: str = ...
    consumer_secret: str = ...
    access_token: str = ...
    token_secret: str = ...

class ArxivTweet(pydantic.BaseModel):
    tweet_id: int = ...
    created_at: datetime = ...
    arxiv_ids: List[str] = ...
    edited_tweet_ids: Optional[List[str]] = None
    likes: int = ...
    retweets: int = ...
    replies: int = ...
    quotes: int = ...
    impressions: int = ...

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

class TwitterAPI():
    def __init__(self):
        with open("private/tweets_auth.yaml", "r") as f:
            yml = yaml.safe_load(f)
            self.credentials = TweetCredentials.parse_obj(yml)
    
    # @staticmethod
    # def is_retweet(tweet):
    #     ref_tweets = tweet.get("referenced_tweets")
    #     if ref_tweets:
    #         for t in ref_tweets:
    #             if t["type"] == "retweet":
    #                 return True
    #     return False

    @staticmethod
    def get_arxiv_ids(tweet):
        results = []
        urls = maybe_get(tweet, ["entities", "urls"], [])
        for url in urls:
            arxiv_id = arxiv.maybe_arxiv_url_to_id(url.get("expanded_url"))
            if arxiv_id:
                results.append(arxiv_id)
        return results if len(results) else None

    @staticmethod
    def maybe_parse_arxiv_tweet(tweet):
        arxiv_ids = TwitterAPI.get_arxiv_ids(tweet)
        if not arxiv_ids:
            return None
        tweet_id = tweet['id']
        edited_ids = [i for i in tweet["edit_history_tweet_ids"] if i != tweet_id]
        metrics = tweet["public_metrics"]
        arxiv_tweet = ArxivTweet(
            tweet_id=tweet_id,
            arxiv_ids=arxiv_ids,
            edited_tweet_ids=edited_ids,
            created_at=util.iso_to_datetime(tweet['created_at']),
            likes=metrics["like_count"],
            retweets=metrics["retweet_count"],
            quotes=metrics["quote_count"],
            replies=metrics["reply_count"],
            impressions=metrics["impression_count"]
        )
        return arxiv_tweet

    def search_for_arxiv(
        self,
        start_time=None,
        end_time=None,
        max_results_per_page=10,
        max_pages=1
    ):
        responses = self.api_search(
            query="arxiv.org",
            start_time=start_time,
            end_time=end_time,
            max_results_per_page=max_results_per_page,
            max_pages=max_pages)

        arxiv_tweets = []
        for response in responses:
            tweets = response.get("data", [])
            referenced_tweets = maybe_get(response, ["includes", "tweets"], [])

            # Get links from referenced tweets
            # Record the ones we see here so we don't repeat with main results.
            seen = set()
            if referenced_tweets:
                for tweet in referenced_tweets:
                    parsed_tweet = self.maybe_parse_arxiv_tweet(tweet)
                    if parsed_tweet is not None:
                        arxiv_tweets.append(parsed_tweet)
                        seen.add(parsed_tweet.tweet_id)

            # Get links from direct tweets. Right now we are just ignoring direct tweets
            # that point to reference tweets since their retweet/metric counts seem off.
            for tweet in tweets:
                parsed_tweet = self.maybe_parse_arxiv_tweet(tweet)
                if parsed_tweet is not None and parsed_tweet.tweet_id not in seen:
                    arxiv_tweets.append(parsed_tweet)
        return arxiv_tweets

    def api_search(
            self,
            query,
            max_results_per_page=10,
            max_pages=1,
            next_token=None,
            return_next_token=False,
            start_time=None,
            end_time=None):
        """Searches the Twitter API with optional pagination. Returns a list of response objects,
        one per page.

        Args:
            query: Query to search for
            max_results_per_page: Max results per page. Defaults to 10.
            max_pages: Number of pages to paginate through (max). Defaults to 1.
            next_token: Token from the API indicating where to resume results from. Defaults to None.
            return_next_token: Whether to return the next_token in addition to the response. Defaults to False.

        Returns:
            responses
            OR
            (responses, next_token)
        """
        if start_time:
            start_time = util.datetime_to_iso(start_time)
        if end_time:
            end_time = util.datetime_to_iso(end_time)
        result = []
        for _ in range(max_pages):
            params = {
                "query": query,
                "max_results": max_results_per_page,
                "tweet.fields": "entities,public_metrics",
                "expansions": "referenced_tweets.id",
                "next_token": next_token,
                "start_time": start_time,
                "end_time": end_time
            }
            params = {k: v for k, v in params.items() if v is not None}
            response = self.request_raw(API_SEARCH_ENDPOINT, params)
            result.append(response)
            next_token = maybe_get(response, ["meta", "next_token"])
            if not next_token:
                break

        if return_next_token:
            return result, next_token
        else:
            return result

    def request_raw(self, url, params, retries=3):
        """Makes a request to the Twitter API with the appropriate credentials

        Args:
            url: API endpoint URL
            params: Dict of params
            retries: Number of retries

        Returns:
            Raw response as a dict.
        """
        with open("private/sample_twitter_response.json", "r") as f:
            return json.load(f)

        with requests.Session() as s:
            retries = Retry(
                total=retries,
                backoff_factor=0.1,
                status_forcelist=[500, 502, 503, 504])
            s.mount('https://', HTTPAdapter(max_retries=retries))
            header = {
                "Authorization": f"Bearer {self.credentials.bearer_token}"
            }
            response = s.get(url, headers=header, params=params)
        return response.json()

