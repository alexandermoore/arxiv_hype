from lib import database, twitter, twitter_v2
import logging


def run(start_dt=None, max_results=1000, num_time_blocks=None):
    api = twitter_v2.TwitterAPIV2()
    db = database.Database()

    # Search Twitter
    # TODO: Parameters like start date, number of tweets, etc.
    # tweets = api.search_for_arxiv(
    #     start_time=start_dt,
    #     max_results_per_page=max_results_per_page,
    #     max_pages=max_pages,
    # )
    tweets = api.search_for_arxiv(
        start_time=start_dt, max_results=max_results, num_time_blocks=num_time_blocks
    )

    # Add results to DB
    logging.info(f"Found {len(tweets)} tweets.")
    db.insert_tweets(tweets)
    db.update_arxiv_social_metrics(update_twitter=True)


if __name__ == "__main__":
    run()
