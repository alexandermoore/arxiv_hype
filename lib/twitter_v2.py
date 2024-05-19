import requests
from requests.adapters import HTTPAdapter, Retry
import pydantic
from datetime import datetime, timedelta
from typing import List, Optional
import bs4
import time
import logging

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


"""
Options for scrapers
"""


class ActorRequest(pydantic.BaseModel):
    actor_id: str
    params: dict


class ApifyActor:
    def __init__(self):
        pass

    def _extract_urls_from_tweet(self, tweet: dict):
        raise NotImplementedError()

    def _get_arxiv_ids(self, tweet: dict):
        urls = self._extract_urls_from_tweet(tweet)
        results = []
        for url in urls:
            arxiv_ids = arxiv.maybe_text_to_arxiv_ids(url)
            if arxiv_ids:
                # will only find one ID in a single URL
                results.append(arxiv_ids[0])
        return results if len(results) else None

    def maybe_parse_arxiv_tweet(self, tweet: dict):
        arxiv_ids = self._get_arxiv_ids(tweet)
        if arxiv_ids is not None:
            return self._tweet_to_arxiv_tweet(tweet, arxiv_ids)

    def _tweet_to_arxiv_tweet(self, tweet: dict, arxiv_ids: List[str]):
        raise NotImplementedError()

    def create_launch_request(
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
        raise NotImplementedError()


class FlashActor(ApifyActor):
    def _extract_urls_from_tweet(self, tweet: dict):
        return maybe_get(tweet, ["tweet_links"], [])

    def _tweet_to_arxiv_tweet(self, tweet: dict, arxiv_ids: List[str]):
        arxiv_tweet = ArxivTweet(
            tweet_id=tweet["tweet_id"],
            arxiv_ids=arxiv_ids,
            edited_tweet_ids=[],
            created_at=util.multi_formats_to_datetime(tweet["timestamp"]),
            likes=tweet["likes"],
            retweets=tweet["retweets"],
            quotes=tweet["quotes"],
            replies=tweet["replies"],
            impressions=0,
        )
        return arxiv_tweet

    def create_launch_request(
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
            "newer_than": util.datetime_to_date_str(start_time),
            "older_than": util.datetime_to_date_str(end_time + timedelta(days=1)),
        }
        params = {k: v for k, v in params.items() if v is not None}
        # return ActorRequest(actor_id="wHMoznVs94gOcxcZl", params=params)
        return ActorRequest(actor_id="shanes~tweet-flash", params=params)


class TwScraperActor(ApifyActor):
    # https://twitter.com/search?f=top&q=wikipedia%20until%3A2022-09-14%20since%3A2019-11-16&src=typed_query
    def _extract_urls_from_tweet(self, tweet: dict):
        urls = maybe_get(tweet, ["entities", "urls"], [])
        return [url.get("expanded_url") for url in urls]

    def _tweet_to_arxiv_tweet(self, tweet: dict, arxiv_ids: List[str]):
        tweet_id = tweet["id_str"]
        edited_ids = []  # [i for i in tweet["edit_history_tweet_ids"] if i != tweet_id]
        arxiv_tweet = ArxivTweet(
            tweet_id=tweet_id,
            arxiv_ids=arxiv_ids,
            edited_tweet_ids=edited_ids,
            created_at=util.multi_formats_to_datetime(tweet["created_at"]),
            likes=tweet["favorite_count"],
            retweets=tweet["retweet_count"],
            quotes=tweet["quote_count"],
            replies=tweet["reply_count"],
            impressions=tweet["views_count"],
        )
        return arxiv_tweet

    def create_launch_request(
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
        params = {
            "searchTerms": [query],
            "searchMode": "top",
            "maxTweets": max_results,
            "addUserInfo": True,
            "scrapeTweetReplies": True,
        }
        if start_time:
            params["sinceDate"] = util.datetime_to_date_str(start_time)
        if end_time:
            params["untilDate"] = util.datetime_to_date_str(
                end_time + timedelta(days=1)
            )
        params = {k: v for k, v in params.items() if v is not None}
        return ActorRequest(actor_id="microworlds~twitter-scraper", params=params)

    def create_launch_request_old(
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
        query = [query]
        if start_time:
            query.append(f"since:{util.datetime_to_date_str(start_time)}")
        if end_time:
            query.append(
                f"until:{util.datetime_to_date_str(end_time + timedelta(days=1))}"
            )
        if min_likes:
            query.append(f"min_faves:{min_likes}")
        if min_retweets:
            query.append(f"min_retweets:{min_retweets}")
        if min_replies:
            query.append(f"min_replies:{min_replies}")
        if has_engagement:
            query.append(f"filter:has_engagement")
        query.append("filter:links")
        query = " ".join(query)
        # may have search mode "top" in both url and param but is fine
        params = {
            "urls": [f"https://twitter.com/search?f=top&q={query}&src=typed_query"],
            "searchMode": "top",
            "maxTweets": max_results,
        }
        params = {k: v for k, v in params.items() if v is not None}
        return ActorRequest(actor_id="microworlds~twitter-scraper", params=params)


class TweetScraperAPIDojoActor(ApifyActor):
    # https://twitter.com/search?f=top&q=wikipedia%20until%3A2022-09-14%20since%3A2019-11-16&src=typed_query
    def _extract_urls_from_tweet(self, tweet: dict):
        urls = maybe_get(tweet, ["entities", "urls"], [])
        return [url.get("expanded_url") for url in urls]

    def _tweet_to_arxiv_tweet(self, tweet: dict, arxiv_ids: List[str]):
        tweet_id = tweet["id"]
        edited_ids = []  # [i for i in tweet["edit_history_tweet_ids"] if i != tweet_id]
        arxiv_tweet = ArxivTweet(
            tweet_id=tweet_id,
            arxiv_ids=arxiv_ids,
            edited_tweet_ids=edited_ids,
            created_at=util.multi_formats_to_datetime(tweet["createdAt"]),
            likes=tweet["likeCount"],
            retweets=tweet["retweetCount"],
            quotes=tweet["quoteCount"],
            replies=tweet["replyCount"],
            # Sometimes missing
            impressions=tweet.get("viewCount", 0),
        )
        return arxiv_tweet

    def create_launch_request(
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
        params = {
            "searchTerms": [query],
            "sort": "Top",
            "maxTweetsPerQuery": max_results,
            "addUserInfo": True,
            "scrapeTweetReplies": True,
            "minimumFavorites": min_likes,
            "minimumRetweets": min_retweets,
            "minimumReplies": min_replies,
        }
        if start_time:
            params["start"] = util.datetime_to_date_str(start_time)
        if end_time:
            params["end"] = util.datetime_to_date_str(end_time + timedelta(days=1))
        params = {k: v for k, v in params.items() if v is not None}
        return ActorRequest(actor_id="apidojo~tweet-scraper", params=params)


# TODO: Move functionality to ApifyActor so we can easily pick one to use at any given time.
# TODO: Check out https://console.apify.com/actors/61RPP7dywgiy0JPD0/information/latest/readme


class TwitterAPIV2:
    def __init__(self, actor: ApifyActor = TweetScraperAPIDojoActor()):
        self.credentials = TweetCredentials(
            api_token=util.get_env_var("APIFY_API_TOKEN")
        )
        self.actor = actor

    def search_for_arxiv(
        self, start_time=None, end_time=None, max_results=10, num_time_blocks=None
    ):
        # Attempt to pull tweets 3 times
        tweets = []
        tries_remaining = 3
        while len(tweets) <= 1 and tries_remaining > 0:
            logging.info(f"Attempting to pull tweets")
            tweets = self.api_search(
                query="arxiv.org",
                start_time=start_time,
                end_time=end_time,
                max_results=max_results,
                num_time_blocks=num_time_blocks,
            )
            tries_remaining -= 1

        arxiv_tweets = []
        seen = set()
        logging.info(f"Processing {len(tweets)} tweets...")

        # Get links from direct tweets. Right now we are just ignoring direct tweets
        # that point to reference tweets since their retweet/metric counts seem off.
        for tweet in tweets:
            parsed_tweet = self.actor.maybe_parse_arxiv_tweet(tweet)
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
        num_time_blocks=None,
    ) -> List[dict]:
        import json

        # with open("private/sample_apify_response_twscrape.json", "r") as f:
        #     return json.load(f)
        if num_time_blocks:
            if not start_time:
                raise ValueError("Must provide start_time when using num_time_blocks")
            if end_time is None:
                end_time = datetime.now()
            time_intervals = util.create_intervals(
                0, (end_time - start_time).days, num_blocks=num_time_blocks
            )
            time_intervals = [
                (start_time + timedelta(days=s), start_time + timedelta(days=e))
                for s, e in time_intervals
            ]
        else:
            time_intervals = [(start_time, end_time)]

        timeout = 60 * 5
        all_results = []
        logging.info(time_intervals)

        # For when a run fails to parse and we want to get its results again without re-requesting
        debug_run_id = None  # "aNQDAPcYM3p6eU39S"

        def _dataset_url(run_id):
            return f"https://api.apify.com/v2/actor-runs/{run_id}/dataset/items"

        def _check_run_finished(run_id):
            url = f"https://api.apify.com/v2/actor-runs/{run_id}"
            result = self.request_raw(url, params={}, retries=1)
            return result["data"]["status"] == "SUCCEEDED"

        for st, et in time_intervals:
            logging.info(f"Searching time interval {(st, et)}")

            if debug_run_id is None:
                actor_request = self.actor.create_launch_request(
                    query=query,
                    max_results=max_results,
                    has_engagement=has_engagement,
                    min_likes=min_likes,
                    min_replies=min_replies,
                    min_retweets=min_retweets,
                    start_time=st,
                    end_time=et,
                )
                launch_run_url = (
                    f"https://api.apify.com/v2/acts/{actor_request.actor_id}/runs"
                )

                run_info = self.request_raw(
                    launch_run_url,
                    params=actor_request.params,
                    retries=1,
                    request_type="post",
                )
                logging.info(f"run_info: {run_info}")
                run_id = run_info["data"]["id"]
            else:
                run_id = debug_run_id

            stime = time.time()
            while time.time() - stime <= timeout and not _check_run_finished(run_id):
                logging.info(
                    f"Waiting for run to complete... ({int(time.time() - stime)}/{timeout}s elapsed)"
                )
                time.sleep(10)
            results = self.request_raw(
                _dataset_url(run_id), params={"format": "json", "clean": "true"}
            )
            logging.info(f"Found {len(results)} tweets in interval.")
            all_results.append(results)
        return [result for results in all_results for result in results]

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
            print("=================REQUESTING======================")
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
