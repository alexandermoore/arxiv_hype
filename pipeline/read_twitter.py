from lib import database, twitter


def run(start_dt=None, max_results_per_page=100, max_pages=20):
    api = twitter.TwitterAPI()
    db = database.Database()

    # Search Twitter
    # TODO: Parameters like start date, number of tweets, etc.
    tweets = api.search_for_arxiv(
        start_time=start_dt,
        max_results_per_page=max_results_per_page,
        max_pages=max_pages,
    )

    # Add results to DB
    print(f"Found {len(tweets)} tweets.")
    db.insert_tweets(tweets)
    db.update_arxiv_social_metrics()


if __name__ == "__main__":
    run()
