from lib import database, twitter

def run():
    api = twitter.TwitterAPI()
    db = database.Database()
    # Search Twitter
    # TODO: Parameters like start date, number of tweets, etc.
    tweets = api.search_for_arxiv()

    # Handle results
    db.insert_tweets(tweets)

if __name__ == "__main__":
    run()