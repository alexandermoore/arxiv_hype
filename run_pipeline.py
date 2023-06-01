from pipeline import read_twitter, update_arxiv_data, update_arxiv_embeddings
from datetime import datetime, timedelta

if __name__ == "__main__":
    print("Handling Twitter")
    read_twitter.run()  # start_dt=datetime.today() - timedelta(days=2)
    print("Handling arxiv data")
    update_arxiv_data.run()
    print("Handling arxiv embeddings")
    update_arxiv_embeddings.run()
    print("Done.")
