from lib import twitter
from lib import arxiv, database


# api = tweets.TwitterAPI()

# ids = [r.arxiv_ids[0] for r in api.search_for_arxiv()[:3]]
# results = arxiv.get_paper_info(ids)
# print(results)
# #print(results)


db = database.Database()
print(db.get_table_columns(database.Tables.ARXIV))
quit()
# db.create_tables()
# # db.bulk_upsert(database.Tables.TWEET,
# #                id_cols=("tweet_id",),
# #                records=[{"tweet_id": 12345, "likes": 195}])

# api = twitter.TwitterAPI()
# t = api.search_for_arxiv()
# db.insert_tweets(t)

r = db.get_arxiv_ids_without_info()



