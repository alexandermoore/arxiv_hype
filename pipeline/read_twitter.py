from lib import database, twitter

def run(start_dt=None):
    api = twitter.TwitterAPI()
    db = database.Database()
    # Search Twitter
    # TODO: Parameters like start date, number of tweets, etc.
    tweets = api.search_for_arxiv(
        start_time=start_dt,
        max_results_per_page=50,
        max_pages=1)

    # Add results to DB
    db.insert_tweets(tweets)

if __name__ == "__main__":
    run()